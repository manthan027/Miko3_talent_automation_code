CLEAR Framework – Video Count Validation (Video Talent Section)
C – Context

The Video Talent section contains a list of videos displayed to users. The number of videos in this section may change over time as new videos are added or existing videos are removed. The system should be able to detect and validate these changes automatically during test execution.

L – Logic

The validation logic should be based on counting the total number of videos present in the Video Talent section at runtime and comparing it with the expected count or previously stored count.

Validation scenarios:

If new videos are added → count should increase.
If videos are removed → count should decrease.
If no change → count should remain the same.
Script should capture the current video count every time it runs.
Script should compare current count with baseline/previous count.
Script should report whether videos were added, removed, or unchanged.

E – Examples
Scenario	        Previous Count	Current Count	Result
No change	        10	            10	            Pass
Videos added	    10	            15	            Pass – 5 videos added
Videos removed	    10	            7	            Pass – 3 videos removed
Unexpected drop	    10	            0	            Fail
Unexpected spike	10	            200	            Fail

A – Action
Automation/Test Script should:

Navigate to Video Talent section.
Count total number of videos displayed.
Store the count (file / database / variable).
Compare with previous count.
Log result:
Videos Added
Videos Removed
No Change
Fail test if count change is unexpected.

R – Result
The system should:

Accurately detect addition of videos.
Accurately detect removal of videos.
Maintain a record of previous video counts.
Provide clear test result logs showing count difference.
Help QA validate content changes automatically without manual verification.
Simple Validation Logic Formula
Current Video Count – Previous Video Count = Difference
If Difference > 0 → Videos Added
If Difference < 0 → Videos Removed
If Difference = 0 → No Change

Automation Perspective (Best Practice)
Do not only validate count. Also validate:

Video titles
Video IDs
Thumbnail presence
Video playable
No duplicate videos

Because sometimes count may be same but content may change.