# Examples
Coding examples for recruiters and hiring managers to review 

SmileViewer is a simpler full-stack example: 

    it stitches some Databasing, ML models, and websocket networking into a lowish latentcy front end 
  
    some improvements are possible but dependent on the usecase:
    
        EX: Ability to tune the smile ID thresholds in real time or stream with less latency would need advanced video encoding and more peer to peer focus such as WebRTC 
        
        EX: Emotional classification could be done with another ML model as well as facial recognition, re-IDing new faces and periodically checking faces to ensure IDs allign to people 

        EX: Broadcasting of video per client could have limittied time outs per client, variable compression etc. 
        
        EX: DB writes could be WAL, the core functions could be separated further and into other processes or threads as needed, all depedning on HW and usecase etc. 

    
        
