import mediapipe as mp
import numpy as np
from collections import deque
import cv2
import time
import datetime
import os 
import asyncio

class SmileIDer:
    def __init__(self, parent):
        self.parent = parent
        self.LandmarksSubSets = {}
        self.init_media_pipe_face_hands()
        self.state = {
            "persistent_faces": {},
            }
        self.images_dir = os.path.join(os.getcwd(), "server", "data", "images")
        pass

    def init_media_pipe_face_hands(self):
        # Initialize Mediapipe Face Mesh and Hand Mesh
        self.mp_drawing = mp.solutions.drawing_utils # for hand connections
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=3,
            refine_landmarks=True, #more accurate lips
            min_detection_confidence=0.6
        )

        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(min_detection_confidence=0.8, min_tracking_confidence=0.7)
        # Landmark subset definition, basic face features
        self.LandmarksSubSets['LeftI'] = [384, 385, 386, 387, 388, 390, 263, 362, 398, 466, 373, 374, 249, 380, 381, 382]
        self.LandmarksSubSets['LeftIBrow'] = [293, 295, 296, 300, 334, 336, 276, 282, 283, 285]
        self.LandmarksSubSets['RightI'] = [160, 33, 161, 163, 133, 7, 173, 144, 145, 246, 153, 154, 155, 157, 158, 159]
        self.LandmarksSubSets['RightIBrow'] = [65, 66, 70, 105, 107, 46, 52, 53, 55, 63]
        self.LandmarksSubSets['Mouth'] = [0, 267, 269, 270, 13, 14, 17, 402, 146, 405, 409, 415, 291, 37, 39, 40, 178, 308, 181, 310, 
                311, 312, 185, 314, 317, 318, 61, 191, 321, 324, 78, 80, 81, 82, 84, 87, 88, 91, 95, 375]
        self.LandmarksSubSets['face_mesh_subset'] = (
            self.LandmarksSubSets['Mouth'] +
            self.LandmarksSubSets['LeftI'] +
            self.LandmarksSubSets['LeftIBrow'] +
            self.LandmarksSubSets['RightI'] +
            self.LandmarksSubSets['RightIBrow']
        )

    # Head Tilt Detection using Face Aspect Ratio (FAR)
    def calculate_far(self, landmarks): #typically uses all face landmarks
        '''
        Face Aspect Ratio (FAR) from a rotated bounding box.
        USed for HEad Tilt estimates 
        '''
        s = self.state
        w,h = s['w'], s['h']
        # Select the landmarks by iterating through the list of indices
        # I tried focusing on other landmarks like eyes and noise or key features, but this is more robust 
        points = np.array([(p.x * w, p.y * h) for p in landmarks], dtype=np.int32)
        rect = cv2.minAreaRect(points)
        (width, height) = rect[1] 
        # assume all faces are taller than wide
        if width > height:
            width, height = height, width
        # catch bad box
        if width == 0:
            return 0.0, None
        
        far = height / width
        return far, rect
    # Toothy Smile Detection
    @staticmethod
    def calculate_mar(landmarks): #again uses all landmarks, but only looks at a few
        '''effectively mouth openness
            varying openess = talking = false smiles? 
            '''
        left_corner = landmarks[61]
        right_corner = landmarks[291]
        top_lip = landmarks[13]
        bottom_lip = landmarks[14]

        # Calculate the Euclidean distance (hypotnuess) between the points
        horizontal_dist = np.linalg.norm(np.array([left_corner.x, left_corner.y]) - np.array([right_corner.x, right_corner.y]))
        vertical_dist = np.linalg.norm(np.array([top_lip.x, top_lip.y]) - np.array([bottom_lip.x, bottom_lip.y]))

        # Avoid division by zero
        if horizontal_dist == 0:
            return 0.0
        
        mar = vertical_dist / horizontal_dist
        return mar
    # make sure teeth not grimmace, also check for no teeth smile
    def check_smile(self, landmarks, tilt, mar =0, thresh= None):
        '''
        This became a bit complicated and could be 2 functions but isn't due to shared variables
        2 things happen
        1: checks the sum curvature a the lips in a very simple way. this way O faces, barring teeth, etc don't show positive when #2 is true 
        2: checks that lip corners are above the bottom lip by same margin in 1 for simplicity
        both of these alone are not terribley robust, but together the work decently.
        '''
        c = self.controls

        if thresh is None:
            try:
                thresh = c['SMILE_THRESH']
            except KeyError:
                thresh = 0.35
        if tilt <= 0:
            tilt = 1
        left_corner = landmarks[61]
        right_corner = landmarks[291]
        inner_top_lip = landmarks[13]
        inner_bottom_lip = landmarks[14]
        outer_top_lip = landmarks[0]
        outer_bottom_lip = landmarks[17]
        

        # origin = inner center of the bottom lips
        origin_x = inner_bottom_lip.x #(inner_top_lip.x + inner_bottom_lip.x) / 2
        origin_y = inner_bottom_lip.y #(inner_top_lip.y + inner_bottom_lip.y) / 2

        # smile x y axes are mouth center lines
        sx_axis = outer_bottom_lip.x - outer_top_lip.x
        sy_axis = outer_bottom_lip.y - outer_top_lip.y

        # Normalize
        mouth_height = np.sqrt(sy_axis**2 + sx_axis**2) #with lips
        if mouth_height == 0: return -1 # bad detect
        sx_unit = sx_axis / mouth_height
        sy_unit = sy_axis / mouth_height
    
        # Vector from origin to corners
        lc_vec_x, lc_vec_y = left_corner.x - origin_x, left_corner.y - origin_y
        rc_vec_x, rc_vec_y = right_corner.x - origin_x, right_corner.y - origin_y
        # Projection / shadow / mag in new axes 
        lc_new_y = lc_vec_x * sx_unit + lc_vec_y * sy_unit
        rc_new_y = rc_vec_x * sx_unit + rc_vec_y * sy_unit
        
        smile_score = (lc_new_y + rc_new_y) / 2 # np.min([lc_new_y, rc_new_y]) # down is up remeber ... 

        # The threshold relative to the lips's height
        # Tried using largest of lip size, avg works better
        # tried using largest lip curl of the 2, but again avg  seemed better
        # use lip height becausd mouth could be open!
        # use these 2 measurements in case of open mouth
        upper_lip_height = np.linalg.norm(
                                np.array([outer_top_lip.x, outer_top_lip.y]) - np.array([inner_top_lip.x, inner_top_lip.y]))
        lower_lip_height = np.linalg.norm(
                                np.array([outer_bottom_lip.x, outer_bottom_lip.y]) - np.array([inner_bottom_lip.x, inner_bottom_lip.y]))
        lip_hieght= (upper_lip_height + lower_lip_height) /2
        scaled_thresh = lip_hieght * thresh / tilt**2 # if head is a little titled, threshold should be higher

        # Another check for like shouting or O faces that would give false positives 
        # Sum of lip curvature should be pointing upward
        mouth_width = np.linalg.norm(
                            np.array([left_corner.x, left_corner.y]) - np.array([right_corner.x, right_corner.y]))
        if mouth_width == 0: return -1 
        upper_curve = ((right_corner.x - left_corner.x) * (inner_top_lip.y - left_corner.y) - 
                    (right_corner.y - left_corner.y) * (inner_top_lip.x - left_corner.x))
        
        lower_curve = ((right_corner.x - left_corner.x) * (inner_bottom_lip.y - left_corner.y) - 
                    (right_corner.y - left_corner.y) * (inner_bottom_lip.x - left_corner.x))
        total_curvature = -((upper_curve) + lower_curve) / mouth_width
        
        if total_curvature < -scaled_thresh*(2.9*mar): # if probably not yelling, big open smiles should have more curveature 
            if smile_score < -scaled_thresh: # and think smiling 
                return 1
        else:
            return -1
    #Make sure no hand is in our larger, cropping face frame
    @staticmethod
    def check_occlusion(face_bbox, hand_bbox):
        '''Checks if a one bounding box has any overlap with another bounding box.'''
        face_x1, face_y1, face_x2, face_y2 = face_bbox
        hand_x1, hand_y1, hand_x2, hand_y2 = hand_bbox
        if face_x2 < hand_x1 or face_x1 > hand_x2 or face_y2 < hand_y1 or face_y1 > hand_y2:
            return False
        return True

    def get_hands(self, rgb_frame, target_frame):
        s = self.state
        c = self.controls
        w, h = s['w'], s['h']
        hands_in_frame_temp = []
        handIDer = self.hands.process
        hand_results = handIDer(rgb_frame)
        if hand_results.multi_hand_landmarks:
            for hand_landmarks in hand_results.multi_hand_landmarks:
                x_coords = []
                y_coords = []
                for landmark in hand_landmarks.landmark:
                    px, py = int(landmark.x * w), int(landmark.y * h)
                    x_coords.append(px)
                    y_coords.append(py)
                x_min, y_min = min(x_coords), min(y_coords)
                x_max, y_max = max(x_coords), max(y_coords)
                hands_in_frame_temp.append((x_min,y_min,x_max,y_max))
                if c['DRAW_LANDMARKS']:
                    self.mp_drawing.draw_landmarks(
                        image=target_frame,
                        landmark_list=hand_landmarks,
                        connections=self.mp_hands.HAND_CONNECTIONS)
                    #for hand BB
                    x_coords = []
                    y_coords = []
                    for landmark in hand_landmarks.landmark:
                        px, py = int(landmark.x * w), int(landmark.y * h)
                        x_coords.append(px)
                        y_coords.append(py)
                        cv2.circle(target_frame, (px, py), 5, (200, 200, 200), cv2.FILLED)
                    #Make hand BB
                    x_min, y_min = min(x_coords), min(y_coords)
                    x_max, y_max = max(x_coords), max(y_coords)
                    cv2.rectangle(
                        target_frame, 
                        (x_min - c['HAND_PAD'], y_min - c['HAND_PAD']), 
                        (x_max + c['HAND_PAD'], y_max + c['HAND_PAD']), 
                        (0, 0, 255), # Red color for the box
                        2            # Line thickness
                    )
        s['hands_in_frame'] = hands_in_frame_temp

    def get_faces(self, rgb_frame, target_frame):
        s = self.state
        w,h = s['w'], s['h']
        c = self.controls
        current_faces_in_frame = []
        FaceIDer = self.face_mesh.process
        face_results = FaceIDer(rgb_frame)
        if face_results.multi_face_landmarks: #if Faces
            for face_landmarks in face_results.multi_face_landmarks: # for each face
                all_x, all_y = zip(*[[(p.x * w),(p.y * h)] for p in face_landmarks.landmark])
                #min and max x y for bounding boxing
                x_min, x_max = int(min(all_x)), int(max(all_x))
                y_min, y_max = int(min(all_y)), int(max(all_y))
                
                face_bbox= (max(0, x_min - c['FACE_PAD']), max(0, y_min - c['FACE_PAD']), 
                        min(w, x_max + c['FACE_PAD']), min(h, y_max + c['FACE_PAD']))

                # Store face data 
                current_face_center = np.mean([[p.x, p.y] for p in face_landmarks.landmark], axis=0) # no need to scale, descale etc ... 
                current_faces_in_frame.append({
                    'landmarks': face_landmarks.landmark,
                    'center': current_face_center,
                    'face_bbox': face_bbox
                })
                if c['DRAW_LANDMARKS']:
                    landmarks = face_landmarks.landmark
                    for idx in self.LandmarksSubSets['face_mesh_subset']:
                        if idx < len(landmarks):
                            lm = landmarks[idx]
                            x, y = int(lm.x * w), int(lm.y * h)
                            if idx in [0, 1, 13, 14, 17, 61, 291]:
                                cv2.circle(target_frame, (x, y), 2, (0, 0, 255), -1)
                            elif idx in [ 78, 191, 80, 81, 82, 13, 312, 311, 310, 415]:
                                cv2.circle(target_frame, (x, y), 2, (0, 255, 200), -1)
                            elif idx in [ 308, 324, 318, 402, 317, 14, 87, 178, 88, 95]:
                                cv2.circle(target_frame, (x, y), 2, (200, 255, 0), -1)
                            else:
                                cv2.circle(target_frame, (x, y), 2, (255, 0, 0), -1)
        return current_faces_in_frame

    def check_faces(self, current_faces_in_frame):
        s = self.state
        w,h = s['w'], s['h']
        c = self.controls
        persistent_faces = s['persistent_faces']
        next_face_id = self.DB_manager.state['next_face_id']
        current_IDs = set()

        for current_face in current_faces_in_frame: 
            best_match_id = None
            min_dist = float('inf')
            # Find the closest existing face
            for face_id, old_face in persistent_faces.items():
                dist = np.linalg.norm(current_face['center'] - old_face['center'])
                if dist < c['PF_SHIFT_BUFF'] and dist < min_dist: #if this face is pretty close to a prior face point, AND closest,
                    min_dist = dist
                    best_match_id = face_id # then the faces are probably the same

            if best_match_id is not None:
                # since it's a match, update the existing face
                face_data = persistent_faces[best_match_id]
                face_data.update({
                    'landmarks': current_face['landmarks'],
                    'center': current_face['center'],
                    'face_bbox': current_face['face_bbox'],
                    'last_seen': time.time()
                })
                face_data['visibility_count'] += 1 # Increment visibility
                current_IDs.add(best_match_id)
            else:
                # It's a NEW, UNCONFIRMED face, add it to persistent face tracking
                if next_face_id is None:
                    next_face_id = 1
                new_id = next_face_id
                next_face_id += 1
                current_far, _ = self.calculate_far(current_face['landmarks'])
                persistent_faces[new_id] = {
                    'landmarks': current_face['landmarks'],
                    'center': current_face['center'],
                    'face_bbox': current_face['face_bbox'],
                    'mar_history': deque(maxlen=c['FRAME_HISTORY_LEN']),
                    'smile_history': deque(maxlen=c['FRAME_HISTORY_LEN']),
                    'rotated_bb_history': deque(maxlen=c['ROTATED_BB_FRAME_AVERAGE']),
                    'baseline_far': current_far,
                    'smile_status': "Detecting...",
                    'last_seen': time.time(),
                    'visibility_count': 1, # Start counter at 1
                    'worker_task': asyncio.create_task(self.image_saving_worker(new_id)) # Spin up worker
                }
                self.DB_manager.state['next_face_id'] = next_face_id
                current_IDs.add(new_id) #not actually matched, maybe should be current_IDs 
        self.parent.state['persistent_faces'] = persistent_faces
        return current_IDs

    def process_faces(self, frame):
        s = self.state
        c = self.controls
        w,h = s['w'], s['h']
        for face_id, face_data in list(s['persistent_faces'].items()):
            # Remove old faces that haven't been seen for a bit
            if time.time() - face_data['last_seen'] > c['CLEAR_TIME']:
                del s['persistent_faces'][face_id]
                continue
                
            landmarks = face_data['landmarks']
            
            #current face tilt check
            current_far, rotated_face_rect = self.calculate_far(landmarks)
            face_data['rotated_face_rect'] = rotated_face_rect

            #check for current mar / talking
            mar = SmileIDer.calculate_mar(landmarks)
            face_data['mar_history'].append(mar)

            is_not_tilted = True
            baseline = face_data['baseline_far']
            if baseline > 0 and current_far > 0:
                is_not_tilted = current_far > (baseline * c['FAR_TILT_TOLERANCE'])
                smile_status = self.check_smile(landmarks, current_far/baseline, mar)
            else:
                smile_status = self.check_smile(landmarks, 1, mar) # assume tilt factor 1 when issues arise

            if is_not_tilted:
                face_data['smile_history'].append(smile_status)
            else:
                face_data['smile_history'].append(False) # elss smiling detected when on the edge of tilt detection 

            if mar < c['MAR_NEUTRAL_THRESHOLD'] and current_far > face_data['baseline_far']: #if mouth closed and FAR > prior, update max FAR
                face_data['baseline_far'] = current_far

            if len(face_data['mar_history']) == c['FRAME_HISTORY_LEN']: # if the buffer is full
                #check for stable mouth (not talking)
                is_not_talking = np.var(face_data['mar_history']) < c['MAR_VAR_THRESHOLD']
                # Calculate the percentage of frames where corners were up IE smile 
                is_smiling = (sum(1 for smiles in face_data['smile_history'] if smiles == 1) / c['FRAME_HISTORY_LEN']) >= c['SMILE_CONFIDENCE']
                # face_data['last_smile_status'] = face_data['smile_status']
                Status = "Smiling" if is_not_talking and is_smiling and is_not_tilted else "Not Smiling"
                if not is_not_tilted: Status = "Tilted"
                if s['hands_in_frame']:
                    for hand_box in s['hands_in_frame']:
                        if self.check_occlusion(face_data['face_bbox'], hand_box): 
                            Status = 'Occluded'
                face_data['smile_status'] = Status
            # Bounding box only if face has been around a bit
            if face_data['visibility_count'] >= c['MIN_VISIBILITY_FRAMES']:
                if c['DRAW_FACE_BB']:
                    x1, y1, x2, y2 = face_data['face_bbox']
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    # Smile status and Face ID text
                    status_text = f"Face {face_id}: {face_data['smile_status']}" 
                    cv2.putText(frame, status_text, (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
                    if 'rotated_face_rect' in face_data and face_data['rotated_face_rect'] is not None and c['DRAW_ROTATED_BB']:
                        box = cv2.boxPoints(face_data['rotated_face_rect'])
                        box = np.int0(box) #for cv2 contour compatibiltity 
                        cv2.drawContours(frame, [box], 0, (255, 0, 255), 2)
                
                # If smiling, draw a specific box around the mouth
                if face_data['smile_status'] == "Smiling" :
                    mouth_points = np.array([(landmarks[i].x * w, landmarks[i].y * h) for i in self.LandmarksSubSets['Mouth']], dtype=np.int32)
                    all_x, all_y = zip(*mouth_points)
                    x_min, x_max = int(min(all_x)), int(max(all_x))
                    y_min, y_max = int(min(all_y)), int(max(all_y))
                    
                    x1, y1, x2, y2 = (max(0, x_min - c['SMILE_PAD']), max(0, y_min - c['SMILE_PAD']), 
                            min(w, x_max + c['SMILE_PAD']), min(h, y_max + c['SMILE_PAD']))
                    face_data['smile_bbox'] = (x1, y1, x2, y2)
                    if c['DRAW_SMILE_BB']:
                        cv2.rectangle(frame, (x1,y1),(x2,y2), (255, 50, 0), 2)
                        if c['DRAW_ROTATED_BB']:
                            rotated_mouth_rect = cv2.minAreaRect(mouth_points)
                            mouth_box = cv2.boxPoints(rotated_mouth_rect)
                            mouth_box = np.int0(mouth_box)
                            cv2.drawContours(frame, [mouth_box], 0, (255, 255, 0), 2)
                
    async def image_saving_worker(self, face_id):
        '''
        saves the initial confirmed face crop
        then saves smile crops periodically.
        '''
        s = self.state
        c = self.controls
 
        face_dir = os.path.join(self.images_dir, str(face_id))
        os.makedirs(face_dir, exist_ok=True)
        saved_initial_face = False
        
        try:
            #save initial face
            while not saved_initial_face and not self.state['shutdown_event'].is_set():
                if face_id not in s['persistent_faces']:
                    return #kill worker if face lost 
                face_data = s['persistent_faces'][face_id]
                if face_data['visibility_count'] >= c['MIN_VISIBILITY_FRAMES'] and c['RECORD']: #save confirmed face
                    if s['latest_frame'] is not None:
                        x1, y1, x2, y2 = face_data['face_bbox']
                        face_crop = s['latest_frame'][y1:y2, x1:x2]
                        if face_crop.size > 0:
                            await asyncio.to_thread(cv2.imwrite, os.path.join(face_dir, "face.jpg"), face_crop)
                            saved_initial_face = True
                await asyncio.sleep(0.125)
                
            while face_id in s['persistent_faces'] and not s['shutdown_event'].is_set() and c['RECORD']: #monitor for smiles while face is in frame, save them
                if face_id not in s['persistent_faces']:
                    return #kill worker if face lost face_data = persistent_faces[face_id]
                face_data = s['persistent_faces'][face_id]
                if face_data.get('smile_status') == "Smiling" and 'smile_bbox' in face_data:
                    x1, y1, x2, y2 = face_data['smile_bbox']
                    smile_crop = s['latest_frame'][y1:y2, x1:x2]
                    
                    if smile_crop.size > 0:
                        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                        filename = f"smile_{timestamp}.jpg"
                        await asyncio.to_thread(cv2.imwrite, os.path.join(face_dir, filename), smile_crop)
                        self.parent.DB_manager.log_smilemeta_to_db(face_id)
                    await asyncio.sleep(0.25) # save @ 4Hz
                else:
                    await asyncio.sleep(0.125) #catch new smiles faster than 4Hz
        except asyncio.CancelledError:
            raise #approve upstream cancel basically 
        except Exception as e:
            print(f"Error in image saving worker for face {face_id}: {e}")
            raise
