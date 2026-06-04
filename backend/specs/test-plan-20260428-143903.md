# Test Plan for TensaiGPT

**Seed:** tests/seed.spec.ts

---

## 1. Authentication & Landing Page

### 1.1 Initial Page Load
**Steps:**
1. Navigate to https://tensaigptnew-qa.tensai.run/
2. Verify page renders completely
3. Confirm all UI elements are visible

**Expected:**
- Page title displays "Tensai-GPT"
- Welcome section with heading "tensaiGPT" is visible
- Tagline "SMARTER CHATS BRIGHTER IDEAS" displays
- "SSO Login" button is accessible and clickable

### 1.2 SSO Login Flow Initiation
**Steps:**
1. Click "SSO Login" button
2. Wait for redirect to Microsoft authentication
3. Verify Microsoft login page loads

**Expected:**
- User is redirected to Microsoft login portal
- Sign in form appears with email/phone/Skype input field
- "Next" button is visible and functional
- Sign-in options button is available
- Footer links (Terms of use, Privacy & cookies) are present

### 1.3 SSO Login Completion
**Steps:**
1. Enter valid organization credentials
2. Click "Next" button
3. Complete multi-factor authentication if required
4. Wait for redirect back to application
5. Verify dashboard or chat interface loads

**Expected:**
- User is authenticated successfully
- Application redirects to main dashboard
- User profile/session is initialized
- Chat interface becomes accessible

---

## 2. Chat Functionality

### 2.1 Chat Interface Load
**Steps:**
1. Login successfully to TensaiGPT
2. Verify chat window/interface is displayed
3. Check all chat UI components are rendered

**Expected:**
- Chat input area is visible and ready for input
- Message history panel (if applicable) displays
- Send button is accessible
- Chat area is focused and ready for user input

### 2.2 Send Chat Message
**Steps:**
1. Click on chat input field
2. Type a test message: "Hello, how can you help?"
3. Click Send button or press Enter
4. Wait for response

**Expected:**
- Message appears in chat history with user identifier
- Message is properly formatted
- Application processes request without errors
- Response is generated and displayed

### 2.3 Chat Message Formatting
**Steps:**
1. Send message with special characters: "Test @mention #hashtag $special"
2. Send message with line breaks
3. Send message with code snippet (if supported)

**Expected:**
- Special characters are handled correctly
- Line breaks are preserved
- Code formatting displays appropriately
- No console errors occur

### 2.4 Chat History Management
**Steps:**
1. Send multiple messages in sequence
2. Scroll through chat history
3. Verify all messages are retained
4. Check timestamps (if displayed)

**Expected:**
- All messages appear in chronological order
- Message history persists
- Scroll functionality works smoothly
- Timestamps are accurate (if applicable)

### 2.5 Chat Context Switching
**Steps:**
1. Start a new chat conversation
2. Return to previous conversation
3. Verify correct conversation content loads

**Expected:**
- New chat creates separate conversation thread
- Previous conversations are accessible
- Context is maintained independently per conversation
- No message mixing between conversations

---

## 3. Agent Selection

### 3.1 Agent List Display
**Steps:**
1. Verify agent selection interface is visible
2. Check all available agents are listed
3. Confirm each agent has descriptive information

**Expected:**
- Agent list displays completely
- Each agent shows name and/or icon
- Agent descriptions are clear and readable
- Selection mechanism is obvious (radio button, dropdown, etc.)

### 3.2 Select Different Agent
**Steps:**
1. Click on first agent
2. Verify selection is highlighted/confirmed
3. Click on different agent
4. Confirm agent switch is reflected in UI

**Expected:**
- Selected agent is visually highlighted
- Selection change is immediate
- Chat interface updates to reflect agent change
- No console errors on agent switch

### 3.3 Agent-Specific Behavior
**Steps:**
1. Select Agent A
2. Send a test query
3. Note response style/content
4. Switch to Agent B
5. Send identical query
6. Compare responses

**Expected:**
- Each agent provides distinct responses appropriate to its role
- Agent behavior is consistent with its specialization
- No cross-agent data contamination
- Response quality is appropriate for each agent

### 3.4 Agent Persistence
**Steps:**
1. Select a specific agent
2. Send multiple messages
3. Refresh page or navigate away
4. Return to chat

**Expected:**
- Previously selected agent remains active (if persistent)
- Or user can reselect agent after refresh
- No errors occur during agent reselection
- Chat context with selected agent is maintained

---

## 4. File Upload Functionality

### 4.1 File Upload Button Visibility
**Steps:**
1. Open chat interface
2. Look for file upload option/button
3. Verify upload trigger is accessible

**Expected:**
- File upload button/icon is visible and intuitive
- Button is accessible via keyboard and mouse
- Hover state provides feedback

### 4.2 Single File Upload
**Steps:**
1. Click file upload button
2. Select a valid file (e.g., PDF, TXT, DOC)
3. Wait for upload to complete
4. Verify file appears in chat

**Expected:**
- File picker dialog opens correctly
- File can be selected from system
- Upload progress indicator displays (if applicable)
- File is successfully uploaded
- File reference appears in chat message
- No file size or format errors for supported types

### 4.3 Multiple File Upload
**Steps:**
1. Click file upload button
2. Select multiple files at once (if supported)
3. Wait for all files to upload
4. Verify all files are listed

**Expected:**
- Multiple files can be selected simultaneously
- Each file uploads independently
- All files appear in chat history
- Upload order is maintained
- No files are corrupted or lost

### 4.4 Unsupported File Type
**Steps:**
1. Click file upload button
2. Attempt to upload unsupported file type (e.g., .exe, .bin)
3. Wait for validation response

**Expected:**
- Application rejects unsupported file type
- User receives clear error message
- Error message indicates supported file types
- Application remains stable

### 4.5 File Size Limit
**Steps:**
1. Attempt to upload file exceeding size limit
2. Observe application response

**Expected:**
- File upload is rejected if oversized
- User receives error message with size limit information
- Application provides guidance on file size requirements
- No partial upload occurs

### 4.6 File Processing in Chat
**Steps:**
1. Upload a relevant file to chat
2. Ask agent to reference or analyze the file
3. Wait for response

**Expected:**
- Agent acknowledges file receipt
- Agent can reference file content in responses
- File processing does not cause timeouts
- Responses are accurate based on file content
- No file content leaks to other users/conversations

### 4.7 File Download/Access
**Steps:**
1. Upload a file to chat
2. Look for file access option (download, preview)
3. Attempt to access file if option available

**Expected:**
- Files remain accessible throughout conversation
- File download option works correctly
- File preview displays properly (if supported)
- File integrity is maintained

---

## 5. Error Handling & Edge Cases

### 5.1 Network Disconnection
**Steps:**
1. Disable network connectivity during chat
2. Attempt to send message
3. Restore network connection

**Expected:**
- Application shows offline indicator
- Messages are queued or show error state
- Connection recovery is smooth
- No message loss when reconnecting

### 5.2 Session Timeout
**Steps:**
1. Login and wait for session to expire
2. Attempt to send chat message

**Expected:**
- Session expiration is handled gracefully
- User is prompted to re-authenticate
- Chat state is preserved if possible
- Re-login returns user to previous conversation

### 5.3 Input Validation
**Steps:**
1. Send empty message
2. Send extremely long message (>5000 characters)
3. Send message with only whitespace

**Expected:**
- Empty messages are rejected or ignored
- Long messages are either accepted or truncated appropriately
- Whitespace-only messages are rejected
- Appropriate validation messages display

---

## 6. Performance & Stability

### 6.1 Chat Responsiveness
**Steps:**
1. Send rapid sequential messages
2. Monitor response time and UI responsiveness
3. Check for lag or freezing

**Expected:**
- All messages are sent and received
- UI remains responsive
- No dropped messages
- Response times are acceptable (<3 seconds typically)

### 6.2 File Upload Performance
**Steps:**
1. Upload file and monitor upload speed
2. Continue chatting while file uploads
3. Verify no UI blocking

**Expected:**
- Upload completes in reasonable time
- UI remains responsive during upload
- Other chat functions work while uploading
- Large files don't crash the application

### 6.3 Memory & Resource Usage
**Steps:**
1. Maintain long chat conversation (50+ messages)
2. Monitor browser memory usage
3. Upload multiple large files
4. Check for memory leaks

**Expected:**
- Memory usage remains stable
- Application doesn't crash with long history
- No noticeable slowdown over time
- Browser continues to run smoothly

---

## 7. Accessibility & User Experience

### 7.1 Keyboard Navigation
**Steps:**
1. Navigate to chat without mouse
2. Tab through all interactive elements
3. Use Enter/Space to activate buttons
4. Test keyboard shortcuts (if available)

**Expected:**
- All controls are keyboard accessible
- Tab order is logical
- Focus indicators are visible
- Keyboard shortcuts function correctly

### 7.2 Responsive Design
**Steps:**
1. Test on desktop (1920x1080)
2. Test on tablet (768x1024)
3. Test on mobile (375x667)
4. Verify chat functionality on each

**Expected:**
- Layout adapts appropriately to screen size
- All features are accessible on mobile
- Chat is usable and readable on all devices
- File upload works on mobile
- No horizontal scrolling on mobile

---

## 8. Security & Data Protection

### 8.1 Session Security
**Steps:**
1. Verify HTTPS connection
2. Check for secure session cookies
3. Attempt to access application without valid session

**Expected:**
- Connection uses HTTPS
- Session cookies have secure flags
- Unauthenticated access is blocked
- Redirect to login occurs

### 8.2 File Upload Security
**Steps:**
1. Upload file with potentially malicious content
2. Verify file is scanned/validated
3. Check file is stored securely

**Expected:**
- Files are validated before processing
- Malicious files are detected and rejected
- Files are stored securely
- No code execution from uploaded files

### 8.3 Data Privacy
**Steps:**
1. Upload sensitive file
2. Verify it's not visible to other users
3. Check conversation is private

**Expected:**
- Files and conversations are user-specific
- No data leakage between users
- Conversations are properly isolated
- Users cannot access others' data

---

## Test Execution Priority

**High Priority:**
- 1.2, 1.3 (Authentication)
- 2.1, 2.2 (Basic Chat)
- 3.2 (Agent Selection)
- 4.2 (File Upload)

**Medium Priority:**
- 2.3, 2.4, 2.5 (Chat Features)
- 3.1, 3.3, 3.4 (Agent Features)
- 4.3, 4.6 (File Management)
- 6.1 (Performance)

**Low Priority:**
- 5.x (Error Cases - regression testing)
- 6.2, 6.3 (Performance)
- 7.x, 8.x (Accessibility & Security)