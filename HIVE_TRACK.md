# HiveBuzz - Hive Track Submission

## Team Name
VKrishna Dev Team

## Project Description
HiveBuzz is a decentralized social media application built on the Hive blockchain. It allows users to authenticate using Hive Keychain, view posts from the dbuzz platform, and create their own posts that are stored permanently on the blockchain.

## Hive Track Requirements Implementation

### 1. Read Data from the Hive Blockchain

Our application reads data from the Hive blockchain in several ways:

#### User Profile Data
We fetch user profile information using the Hive API:

```python
# From app.py - profile route
response = requests.post(
    API_URL,
    json={
        "jsonrpc": "2.0",
        "method": "condenser_api.get_accounts",
        "params": [[username]],
        "id": 1
    },
    headers={"Content-Type": "application/json"}
)
```

#### Feed Content
We load posts from the Hive blockchain via the dbuzz API:

```python
# From app.py - posts route
response = requests.get(
    f"{DBUZZ_API_URL}/posts",
    params={"limit": 10},
    headers={"Accept": "application/json"},
    timeout=5
)
```

### 2. Broadcast Transactions to the Hive Blockchain

Users can create and publish posts directly to the Hive blockchain:

```javascript
// Using Hive Keychain in templates/create_post.html
window.hive_keychain.requestBroadcast(
  username,
  operations,
  "posting",
  (response) => {
    // Handle response
  }
);
```

### 3. Perform Login by Interacting with Hive Keychain

Our application implements secure authentication through Hive Keychain:

```javascript
// From templates/login.html
window.hive_keychain.requestSignBuffer(
  username,
  message,
  "Posting",
  (response) => {
    if (response.success) {
      // Submit the form with the signed message
      document.getElementById("signature-input").value = response.result;
      document.getElementById("keychain-form").submit();
    }
  }
);
```

## Additional Features

### User Profile System
Users can view their profile information fetched directly from the Hive blockchain, including:
- Profile image
- About information
- Post count
- Follower count
- Following count

### Error Handling
We've implemented robust error handling with:
- Graceful degradation with mock data when the API is unavailable
- User-friendly error messages
- Custom error pages

## Screenshots

![Login Screen](path/to/login-screenshot.png)
![Feed View](path/to/feed-screenshot.png)
![Post Creation](path/to/post-creation-screenshot.png)
![User Profile](path/to/profile-screenshot.png)

## Future Enhancements

1. **HiveAuth Implementation**: Add support for HiveAuth as an alternative login method
2. **Comment System**: Enable users to comment on posts
3. **Voting System**: Implement upvoting/downvoting functionality
4. **Wallet Integration**: Add wallet features to view and manage HIVE tokens

## Technical Details

### Libraries Used
- Flask 2.2.3
- Requests 2.28.2
- Python-dotenv 1.0.0

### Additional Hive APIs
1. `condenser_api.get_accounts` - For fetching user account data
2. `condenser_api.get_content` - For retrieving post content
3. `condenser_api.get_discussions_by_created` - For fetching recent posts

## Conclusion

HiveBuzz demonstrates the power of building decentralized applications on the Hive blockchain. By leveraging Hive's robust infrastructure, we've created a censorship-resistant social media platform that gives users control over their data and content.
