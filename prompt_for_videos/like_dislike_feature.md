I want to implement a toggle-based “Like/Dislike” functionality for stories with integration into the Favorites section.

Requirement Overview:
When a user likes a story, it should be added to the Favorites section.
If the user navigates to the Favorites section and clicks the Like button again on the same story, it should:
Automatically switch to Disliked state
Remove the story from the Favorites section
Expected Behavior:
The Like button acts as a toggle (Like ↔ Dislike).
The Favorites count should dynamically update based on user actions.
Example Scenario:
Initially, there are 5 stories in the Favorites section.
The user opens the Favorites section.
The user clicks the Like button on one of the stories (which is already liked).
The story should be removed from Favorites.
The updated count should now be 4 stories.
Key Logic Requirement:
Ensure that state synchronization (UI + backend/data) is consistent.
Any toggle action should immediately reflect in:
Story state (liked/disliked)
Favorites list
Favorites count