# HiveBuzz Project TODO

## Backend Tasks
- [x] Set up basic Flask application structure
- [x] Implement login with Hive Keychain
- [x] Implement login with HiveAuth
- [x] Implement login with HiveSigner
- [x] Create user session management
- [x] Implement basic post listing functionality
- [x] Implement user profile page with real data fetching
- [x] Implement post detail view with real data fetching
- [ ] Connect to Hive blockchain for real content
- [ ] Implement commenting system with Hivemind
- [ ] Set up real upvoting functionality
- [ ] Implement reblog functionality
- [ ] Create follow/unfollow functionality
- [ ] Implement user notifications system
- [ ] Add search functionality for posts and users
- [ ] Set up pagination for post listings
- [ ] Implement user settings storage and retrieval
- [ ] Create wallet functionality for HIVE/HBD transactions
- [ ] Set up secure interactions with Hive blockchain
- [ ] Implement post creation with proper permlink generation
- [ ] Add post editing functionality

## Frontend Tasks
- [x] Design and implement the base template
- [x] Create responsive navigation menu
- [x] Design the login page with multiple authentication options
- [x] Improve login page UI/UX with better visual guidance
- [x] Implement dark mode toggle
- [x] Create user profile page layout
- [x] Implement dashboard with user stats
- [x] Design post listing page
- [x] Create post detail view with comments
- [x] Add post creation form with preview
- [x] Design wallet interface for managing funds
- [x] Implement charts/graphs for user activity metrics
- [x] Show real data for authenticated users vs. demo data for demo users
- [ ] Create a more user-friendly editor for post creation
- [ ] Add responsive design improvements for mobile users
- [ ] Create loading states and placeholder animations
- [ ] Implement infinite scroll for post/comment listings
- [ ] Add custom theme color selection
- [ ] Design notification center UI
- [ ] Create user settings page
- [ ] Implement avatar uploading and profile customization

## Data Tasks
- [x] Set up demo posts for testing
- [x] Use actual user profile data from Hive blockchain
- [x] Differentiate between demo data and real blockchain data
- [ ] Set up caching for API responses
- [ ] Implement database for storing app-specific data
- [ ] Create data models for users, posts, and comments
- [ ] Add analytics for tracking user engagement
- [ ] Set up scheduled tasks for data updates
- [ ] Create backup system for user preferences

## DevOps Tasks
- [ ] Set up CI/CD pipeline
- [ ] Configure production environment
- [ ] Set up logging and monitoring
- [ ] Implement error tracking and reporting
- [ ] Create Docker containerization for easy deployment
- [ ] Set up automatic backups
- [ ] Configure rate limiting for API endpoints
- [ ] Implement security best practices

## Documentation Tasks
- [ ] Create API documentation
- [ ] Write user manual/guide
- [ ] Document codebase for developers
- [ ] Create contribution guidelines
- [ ] Document deployment process
- [ ] Create changelog system

## Configuration Tasks

### HiveSigner Setup
1. Visit https://hivesigner.com/
2. Login with your Hive account
3. Click on "Dashboard" in the top right
4. Select "Apps" from the menu
5. Click "Create new app"
6. Fill in the form:
   - App Name: The name you want for your app (e.g., "HiveBuzz")
   - Description: Brief description of your application
   - Icon URL: URL to your app's logo (optional)
   - Website URL: Your app's website (e.g., "https://hivebuzz.example.com")
   - Redirect URI(s): Callback URL for authentication (e.g., "http://localhost:5000/hivesigner/callback")
7. Choose permissions (scopes) your app needs:
   - login (required)
   - vote (for post/comment voting)
   - comment (for posting/commenting)
   - offline (for using refresh tokens)
8. Click "Create App"
9. Copy the generated client ID and secret
10. Add them to your `.env` file

## Features to Implement

- [ ] Custom accent color picker in settings
- [ ] Implement full HiveSigner authentication flow
- [ ] Add post scheduling functionality
- [ ] Implement notification system
- [ ] Create mobile responsive layouts

## Bug Fixes

- [ ] Fix dark mode toggle persistence
- [ ] Address form validation issues

## Current Focus
- Improving login page UI/UX
- Implementing real data fetching for authenticated users
- Ensuring demo data only shows for demo logins
