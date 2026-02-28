/**
 * Generates a formatted submission post for Ecency based on project details
 */
const fs = require("fs");
const path = require("path");

const TEAM_NAME = "VKrishna Dev Team";
const PROJECT_NAME = "HiveBuzz";
const GITHUB_REPO = "https://github.com/Life-Experimentalist/HiveBuzz"; // Update with your repo
const DEMO_VIDEO = "https://youtu.be/YOUR-VIDEO-ID"; // Update with your demo video
const WEBSITE_URL = ""; // Fill if deployed

// Read package.json to get dependencies
const packageJson = JSON.parse(
	fs.readFileSync(path.join(__dirname, "package.json"), "utf8")
);
const dependencies = packageJson.dependencies;

// Generate markdown for the submission post
const generateSubmissionPost = () => {
	const submissionContent = `
# ${PROJECT_NAME} - A Decentralized Social Media Application Built on Hive

## Team Information
- **Team Name:** ${TEAM_NAME}
- **GitHub Repository:** [${PROJECT_NAME} on GitHub](${GITHUB_REPO})
- **Demo Video:** [Watch Demo](${DEMO_VIDEO})
${WEBSITE_URL ? `- **Live Website:** [${PROJECT_NAME}](${WEBSITE_URL})` : ""}

## Introduction
Hello Hive community! We're excited to present ${PROJECT_NAME}, our submission for the Hive Track in this hackathon. Our team has built a decentralized social media application that leverages the power of the Hive blockchain for content storage, user authentication, and interactions.

## How We Discovered Hive
Our journey with Hive began when we learned about its potential as a decentralized social blockchain. We were impressed by its speed, fee-less transactions, and the vibrant community built around it. The more we explored, the more we realized that Hive is the perfect foundation for our social media application.

## Project Description
${PROJECT_NAME} is a decentralized social media platform that allows users to:

1. **Authenticate securely** using Hive Keychain
2. **Browse content** from the Hive blockchain
3. **Create and publish posts** directly to the blockchain
4. **View user profiles** with data pulled from the chain

### Key Features

#### 1. Secure Authentication
Users can log in using Hive Keychain, which ensures their private keys never leave their browser:

\`\`\`javascript
window.hive_keychain.requestSignBuffer(
  username,
  message,
  "Posting",
  (response) => {
    // Authentication logic
  }
);
\`\`\`

#### 2. Reading Data from Hive
We fetch posts and user data directly from the Hive blockchain:

\`\`\`javascript
const userData = await getAccountInfo(username);
const posts = await getDbuzzPosts(10);
\`\`\`

#### 3. Broadcasting Transactions
Users can create posts that are broadcasted to the Hive blockchain:

\`\`\`javascript
window.hive_keychain.requestBroadcast(
  username,
  operations,
  "posting",
  (response) => {
    // Handle response
  }
);
\`\`\`

#### 4. User Profiles
Users can view their own profiles with data pulled directly from the blockchain:

\`\`\`javascript
const profile = await getAccountInfo(username);
\`\`\`

### Technology Stack
- **Frontend:** React
- **Blockchain Interaction:** @hiveio/dhive ${dependencies["@hiveio/dhive"]}
- **API Communication:** Axios ${dependencies["axios"]}
- **Authentication:** Hive Keychain

## Hive APIs Used
1. \`condenser_api.get_accounts\` - Fetching user data
2. \`condenser_api.get_content\` - Retrieving post content
3. \`condenser_api.get_discussions_by_created\` - Loading recent posts

## User Experience
We've designed ${PROJECT_NAME} with both functionality and aesthetics in mind. The application includes:

- Responsive design for all devices
- Dark mode support
- Intuitive post creation interface
- Seamless authentication flow

## Challenges and Solutions
During development, we faced several challenges:

1. **Challenge:** Handling authentication securely
   **Solution:** Implemented Hive Keychain for secure key management

2. **Challenge:** Reading and displaying blockchain data efficiently
   **Solution:** Created optimized API calls with proper error handling

3. **Challenge:** Ensuring proper transaction broadcasting
   **Solution:** Implemented robust verification and feedback mechanisms

## Future Development
We have exciting plans for ${PROJECT_NAME}'s future:

1. Adding support for HiveAuth
2. Implementing commenting and voting functionality
3. Adding wallet features for managing HIVE tokens
4. Creating a notification system
5. Adding support for content monetization

## Hackathon Experience
Participating in this hackathon has been an incredible experience. We've learned so much about blockchain development, particularly on the Hive chain. The community support and technical resources provided were invaluable in helping us bring our idea to life.

## Conclusion
${PROJECT_NAME} demonstrates the power of building decentralized applications on Hive. We're excited to continue developing and improving this platform, and we welcome feedback from the community.

Thank you for the opportunity to participate in this hackathon!

#hive #blockchain #socialmedia #decentralized #hackathon
`;

	return submissionContent;
};

// Write the submission post to a file
const submissionContent = generateSubmissionPost();
const outputPath = path.join(__dirname, "SUBMISSION_POST.md");

fs.writeFileSync(outputPath, submissionContent);
console.log(`Submission post has been generated at: ${outputPath}`);
console.log("You can copy this content and post it on Ecency.com");
