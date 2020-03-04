# cat2loc
predict exact fine grained user location based on the location category 



For a given category e.g. coffee shop,

1.  Score all candidate coffee shops visited by user in the past by

    a. Frequency of the users past visit
    b. Distance to user mode location(s)
    c. Time difference between the target visit and the average time of the day when user visited each candidate coffee shop
    
2. If user visited no other coffee shop in the past, then score all possible coffee shops by

    a. Distance to user mode location(s)
    b. Frequency of the users friends past visits
    c. Difference in time from the average time of the day when users' friends visited each candidate coffee shop
    d. Distance to users friends' mode locations
    
    


