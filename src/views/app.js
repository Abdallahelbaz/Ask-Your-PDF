// ==================== DOM ELEMENTS ====================
const textarea = document.getElementById('userInput');
const welcomeScreen = document.getElementById('welcomeScreen');
const chatMessages = document.getElementById('chatMessages');
const loading = document.getElementById('loading');
const sendBtn = document.getElementById('sendBtn');
const themeToggle = document.getElementById('themeToggle');
const themeIcon = document.getElementById('themeIcon');
const fileInput = document.getElementById('fileInput');
const suggestedQuestions = document.getElementById('suggestedQuestions');
const welcomeSubtitle = document.getElementById('welcomeSubtitle');

// ==================== CONFIGURATION ====================
const API_BASE_URL = 'http://localhost:5000';
const API_PATH = '/api/v1/nlp/index/answer';
const DEFAULT_LIMIT = 10;
const CHATS_STORAGE_KEY = 'rag_app_chats_list';

// Project ID mapping
const PROJECT_IDS = {
    'bgb': '3',
};

// ==================== STATE ====================
let isDarkMode = false;
let currentProjectId = '3';
let currentChatId = null;
let chats = [];
let activeMenuId = null; // Track which chat menu is open

// ==================== THEME MANAGEMENT ====================
function initTheme() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-theme');
        themeIcon.textContent = '☀️';
        isDarkMode = true;
    }
}

function toggleTheme() {
    if (isDarkMode) {
        document.body.classList.remove('dark-theme');
        themeIcon.textContent = '🌙';
        localStorage.setItem('theme', 'light');
    } else {
        document.body.classList.add('dark-theme');
        themeIcon.textContent = '☀️';
        localStorage.setItem('theme', 'dark');
    }
    isDarkMode = !isDarkMode;
}

// ==================== CHAT MANAGEMENT ====================
function generateChatId() {
    return 'chat_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

function getChatNameFromFirstMessage(message) {
    return message.length > 30 ? message.substring(0, 30) + '...' : message;
}

function getLastMessageTime(messages) {
    if (!messages || messages.length === 0) return Date.now();
    
    // Find the last message (assuming messages are in order)
    const lastMessage = messages[messages.length - 1];
    return lastMessage.timestamp || Date.now();
}

function saveChatsToStorage() {
    localStorage.setItem(CHATS_STORAGE_KEY, JSON.stringify(chats));
}

function loadChatsFromStorage() {
    const saved = localStorage.getItem(CHATS_STORAGE_KEY);
    if (saved) {
        try {
            chats = JSON.parse(saved);
            renderChatHistory();
        } catch (e) {
            console.error('Failed to load chats:', e);
            chats = [];
        }
    }
}

function closeAllMenus() {
    document.querySelectorAll('.chat-menu-dropdown').forEach(menu => menu.remove());
    activeMenuId = null;
}

function toggleChatMenu(chatId, event, buttonElement) {
    event.stopPropagation();
    
    // Close any open menu
    closeAllMenus();
    
    if (activeMenuId === chatId) {
        activeMenuId = null;
        return;
    }
    
    activeMenuId = chatId;
    
    // Create dropdown menu
    const dropdown = document.createElement('div');
    dropdown.className = 'chat-menu-dropdown';
    dropdown.style.cssText = `
        position: absolute;
        right: 30px;
        top: 30px;
        background: var(--container-bg);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        z-index: 1000;
        min-width: 60px;
        overflow: hidden;
        width: 120px
    `;
    
    const chat = chats.find(c => c.id === chatId);
    if (!chat) return;
    
    // Pin option
    const pinOption = document.createElement('div');
    pinOption.className = 'menu-item';
    pinOption.style.cssText = `
        padding: 10px 15px;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 8px;
        transition: background 0.2s ease;
        color: var(--text-primary);
    `;
    pinOption.innerHTML = chat.pinned ? '📌 Unpin' : '📌 Pin';
    pinOption.addEventListener('mouseenter', () => {
        pinOption.style.background = 'var(--action-btn-hover-bg)';
    });
    pinOption.addEventListener('mouseleave', () => {
        pinOption.style.background = 'transparent';
    });
    pinOption.addEventListener('click', (e) => {
        e.stopPropagation();
        togglePinChat(chatId);
        closeAllMenus();
    });
    
    // Delete option
    const deleteOption = document.createElement('div');
    deleteOption.className = 'menu-item';
    deleteOption.style.cssText = `
        padding: 10px 15px;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 8px;
        transition: background 0.2s ease;
        color: #ff4444;
        border-top: 1px solid var(--border-color);
    `;
    deleteOption.innerHTML = '🗑️ Delete';
    deleteOption.addEventListener('mouseenter', () => {
        deleteOption.style.background = 'var(--action-btn-hover-bg)';
    });
    deleteOption.addEventListener('mouseleave', () => {
        deleteOption.style.background = 'transparent';
    });
    deleteOption.addEventListener('click', (e) => {
        e.stopPropagation();
        deleteChat(chatId);
        closeAllMenus();
    });
    
    dropdown.appendChild(pinOption);
    dropdown.appendChild(deleteOption);
    
    // Position the dropdown near the button
    const rect = buttonElement.getBoundingClientRect();
    const containerRect = document.querySelector('.sidebar').getBoundingClientRect();
    
    dropdown.style.position = 'fixed';
    dropdown.style.top = rect.top + 'px';
    dropdown.style.left = (rect.left - 160) + 'px'; // Show to the left of the button
    
    document.body.appendChild(dropdown);
    
    // Close menu when clicking outside
    setTimeout(() => {
        document.addEventListener('click', function closeMenu(e) {
            if (!dropdown.contains(e.target) && e.target !== buttonElement) {
                dropdown.remove();
                activeMenuId = null;
                document.removeEventListener('click', closeMenu);
            }
        });
    }, 0);
}

function togglePinChat(chatId) {
    const chatIndex = chats.findIndex(c => c.id === chatId);
    if (chatIndex >= 0) {
        chats[chatIndex].pinned = !chats[chatIndex].pinned;
        saveChatsToStorage();
        renderChatHistory();
    }
}

function deleteChat(chatId) {
    if (confirm('Are you sure you want to delete this chat?')) {
        chats = chats.filter(chat => chat.id !== chatId);
        
        if (chatId === currentChatId) {
            if (chats.length > 0) {
                const sortedChats = sortChats(chats);
                loadChat(sortedChats[0].id);
            } else {
                createNewChat();
            }
        }
        
        saveChatsToStorage();
        renderChatHistory();
    }
}

function sortChats(chatsArray) {
    // Pinned chats first, then by timestamp
    return [...chatsArray].sort((a, b) => {
        if (a.pinned && !b.pinned) return -1;
        if (!a.pinned && b.pinned) return 1;
        return (b.lastMessageTime || b.timestamp) - (a.lastMessageTime || a.timestamp);
    });
}

function renderChatHistory() {
    const sidebar = document.querySelector('.sidebar-section:last-child');
    if (!sidebar) return;
    
    // Clear existing chat history
    const title = sidebar.querySelector('.sidebar-title');
    sidebar.innerHTML = '';
    if (title) sidebar.appendChild(title);
    
    const sortedChats = sortChats(chats);
    
    if (sortedChats.length === 0) {
        const emptyState = document.createElement('div');
        emptyState.className = 'empty-chats';
        emptyState.style.cssText = `
            padding: 20px;
            text-align: center;
            color: var(--text-muted);
            font-size: 13px;
        `;
        emptyState.textContent = 'No chats yet. Click the theme button to start a new chat!';
        sidebar.appendChild(emptyState);
        return;
    }
    
    sortedChats.forEach(chat => {
        const chatContainer = document.createElement('div');
        chatContainer.className = 'chat-history-container';
        chatContainer.style.cssText = `
            display: flex;
            align-items: center;
            gap: 5px;
            margin-bottom: 10px;
            position: relative;
        `;
        
        const chatElement = document.createElement('div');
        chatElement.className = 'document-item chat-history-item';
        chatElement.dataset.chatId = chat.id;
        chatElement.style.flex = '1';
        chatElement.style.cursor = 'pointer';
        
        if (chat.id === currentChatId) {
            chatElement.classList.add('active');
        }
        
        // Add pin indicator if pinned
        const pinIndicator = chat.pinned ? '📌 ' : '';
        
        // Format date from last message time
        const messageTime = chat.lastMessageTime || chat.timestamp;
        const date = new Date(messageTime);
        
        // Format date based on how recent it is
        let dateStr;
        const today = new Date();
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);
        
        if (date.toDateString() === today.toDateString()) {
            // Today - show time
            dateStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        } else if (date.toDateString() === yesterday.toDateString()) {
            // Yesterday
            dateStr = 'Yesterday';
        } else {
            // Older - show date
            dateStr = date.toLocaleDateString([], { month: 'short', day: 'numeric' });
        }
        
        chatElement.innerHTML = `
            <div class="doc-icon">${chat.pinned ? '📌' : '💬'}</div>
            <div class="doc-info">
                <div class="doc-name">${pinIndicator}${chat.name}</div>
                <div class="doc-meta">${dateStr}</div>
            </div>
        `;
        
        // Three dots menu button
        const menuBtn = document.createElement('button');
        menuBtn.className = 'chat-menu-btn';
        menuBtn.innerHTML = '⋮';
        menuBtn.style.cssText = `
            background: none;
            border: none;
            cursor: pointer;
            font-size: 18px;
            padding: 8px;
            border-radius: 6px;
            color: var(--text-muted);
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 32px;
            height: 32px;
        `;
        menuBtn.title = 'Chat options';
        
        menuBtn.addEventListener('mouseenter', () => {
            menuBtn.style.backgroundColor = 'var(--action-btn-hover-bg)';
            menuBtn.style.color = 'var(--text-primary)';
        });
        menuBtn.addEventListener('mouseleave', () => {
            menuBtn.style.backgroundColor = 'transparent';
            menuBtn.style.color = 'var(--text-muted)';
        });
        
        menuBtn.addEventListener('click', (e) => toggleChatMenu(chat.id, e, menuBtn));
        
        chatElement.addEventListener('click', () => loadChat(chat.id));
        
        chatContainer.appendChild(chatElement);
        chatContainer.appendChild(menuBtn);
        sidebar.appendChild(chatContainer);
    });
}

function createNewChat() {
    if (currentChatId && chatMessages.children.length > 0) {
        saveCurrentChat();
    }
    
    currentChatId = generateChatId();
    const newChat = {
        id: currentChatId,
        name: 'New Chat',
        messages: [],
        timestamp: Date.now(),
        lastMessageTime: Date.now(),
        pinned: false
    };
    
    chats.push(newChat);
    saveChatsToStorage();
    
    chatMessages.innerHTML = '';
    welcomeScreen.style.display = 'flex';
    chatMessages.style.display = 'none';
    
    renderChatHistory();
    console.log('🆕 New chat created:', currentChatId);
}

function saveCurrentChat() {
    if (!currentChatId) return;
    
    const messages = [];
    document.querySelectorAll('.message').forEach(msg => {
        const content = msg.querySelector('.message-content')?.innerText || '';
        const sender = msg.classList.contains('user') ? 'user' : 'assistant';
        messages.push({ 
            content, 
            sender,
            timestamp: Date.now() // Add timestamp to each message
        });
    });
    
    if (messages.length === 0) return;
    
    const chatIndex = chats.findIndex(c => c.id === currentChatId);
    if (chatIndex >= 0) {
        chats[chatIndex].messages = messages;
        chats[chatIndex].timestamp = Date.now();
        chats[chatIndex].lastMessageTime = Date.now();
        
        const firstUserMsg = messages.find(m => m.sender === 'user');
        if (firstUserMsg) {
            chats[chatIndex].name = getChatNameFromFirstMessage(firstUserMsg.content);
        }
    }
    
    saveChatsToStorage();
    renderChatHistory();
}

function loadChat(chatId) {
    if (currentChatId && chatMessages.children.length > 0) {
        saveCurrentChat();
    }
    
    const chat = chats.find(c => c.id === chatId);
    if (!chat) return;
    
    currentChatId = chatId;
    chatMessages.innerHTML = '';
    
    if (chat.messages && chat.messages.length > 0) {
        chat.messages.forEach(msg => {
            addMessage(msg.content, msg.sender, false);
        });
        welcomeScreen.style.display = 'none';
        chatMessages.style.display = 'flex';
    } else {
        welcomeScreen.style.display = 'flex';
        chatMessages.style.display = 'none';
    }
    
    renderChatHistory();
    console.log('📂 Loaded chat:', chatId);
}

// ==================== UI HELPER FUNCTIONS ====================
function resizeTextarea() {
    textarea.style.height = 'auto';
    textarea.style.height = (textarea.scrollHeight) + 'px';
}

function showLoading() {
    loading.classList.add('active');
    sendBtn.disabled = true;
}

function hideLoading() {
    loading.classList.remove('active');
    sendBtn.disabled = false;
}

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function formatMessageContent(content) {
    return content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
}

// ==================== MESSAGE HANDLING ====================
function addMessage(content, sender, saveToStorage = true) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = sender === 'user' ? '👤' : 'AI';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    const lines = content.split('\n');
    let sources = [];
    let mainContent = [];
    
    lines.forEach(line => {
        if (line.toLowerCase().includes('sources:')) {
            return;
        } else if (line.includes('.pdf') || line.includes('Page') || line.includes('source')) {
            sources.push(line.trim());
        } else if (line.trim()) {
            mainContent.push(line);
        }
    });
    
    mainContent.forEach(line => {
        if (line.trim()) {
            const p = document.createElement('p');
            p.innerHTML = formatMessageContent(line);
            contentDiv.appendChild(p);
        }
    });
    
    if (sources.length > 0) {
        const sourcesDiv = document.createElement('div');
        sourcesDiv.className = 'sources';
        
        const sourcesTitle = document.createElement('div');
        sourcesTitle.className = 'sources-title';
        sourcesTitle.textContent = 'Sources:';
        sourcesDiv.appendChild(sourcesTitle);
        
        sources.forEach(source => {
            const tag = document.createElement('span');
            tag.className = 'source-tag';
            tag.textContent = source;
            sourcesDiv.appendChild(tag);
        });
        
        contentDiv.appendChild(sourcesDiv);
    }
    
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    
    scrollToBottom();
    
    if (saveToStorage && currentChatId) {
        saveCurrentChat();
    }
}

// ==================== API COMMUNICATION ====================
async function sendToBackend(question, projectId) {
    const requestBody = {
        text: question,
        limit: DEFAULT_LIMIT
    };
    
    console.log('🚀 Sending request:', {
        url: `${API_BASE_URL}${API_PATH}/${projectId}`,
        body: requestBody
    });
    
    const response = await fetch(`${API_BASE_URL}${API_PATH}/${projectId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
    });
    
    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
    }
    
    return await response.json();
}

function processBackendResponse(data) {
    if (typeof data === 'string') return data;
    if (data.answer) return data.answer;
    if (data.response) return data.response;
    if (data.text) return data.text;
    return JSON.stringify(data, null, 2);
}

// ==================== CORE FUNCTIONALITY ====================
async function sendMessage() {
    const question = textarea.value.trim();
    if (!question) return;

    if (!currentChatId) {
        createNewChat();
    }

    welcomeScreen.style.display = 'none';
    chatMessages.style.display = 'flex';
    
    addMessage(question, 'user');
    
    textarea.value = '';
    resizeTextarea();
    
    showLoading();
    
    try {
        const projectId = getCurrentProjectId();
        const data = await sendToBackend(question, projectId);
        console.log('✅ Received response:', data);
        
        const answerText = processBackendResponse(data);
        addMessage(answerText, 'assistant');
        
    } catch (error) {
        console.error('❌ Error:', error);
        
        let errorMessage = 'Sorry, an error occurred while processing your request.';
        
        if (error.message.includes('Failed to fetch')) {
            errorMessage = '⚠️ Cannot connect to the server. Please make sure the backend is running on http://localhost:5000';
        } else if (error.message.includes('404')) {
            errorMessage = '⚠️ API endpoint not found. Please check the URL.';
        } else if (error.message.includes('422')) {
            errorMessage = '⚠️ Invalid request format. Please check the SearchRequest model.';
        } else if (error.message.includes('Collection') && error.message.includes('not found')) {
            errorMessage = '⚠️ No documents found for this project. Please upload documents first.';
        }
        
        addMessage(errorMessage, 'assistant');
        
    } finally {
        hideLoading();
    }
}

// ==================== PROJECT ID MANAGEMENT ====================
function getCurrentProjectId() {
    const activeDoc = document.querySelector('.sidebar-section:first-child .document-item.active');
    if (!activeDoc) return currentProjectId;
    
    const projectId = activeDoc.dataset.projectId;
    if (projectId) return projectId;
    
    const docName = activeDoc.querySelector('.doc-name')?.textContent || '';
    if (docName.includes('BGB')) return '3';
    
    return currentProjectId;
}

function updateProjectIdFromDocument(docElement) {
    const docName = docElement.querySelector('.doc-name')?.textContent || '';
    
    if (docName.includes('BGB')) {
        currentProjectId = '3';
    } else {
        currentProjectId = docElement.dataset.projectId || currentProjectId;
    }
    
    welcomeSubtitle.innerHTML = `Now viewing: <strong>${docName}</strong><br>Ask questions about this document.`;
}

// ==================== DOCUMENT MANAGEMENT ====================
function createDocumentElement(file) {
    const docElement = document.createElement('div');
    docElement.className = 'document-item';
    
    const baseName = file.name.replace('.pdf', '').replace(/\s+/g, '_').toLowerCase();
    docElement.dataset.projectId = baseName;
    
    docElement.innerHTML = `
        <div class="doc-icon">📄</div>
        <div class="doc-info">
            <div class="doc-name">${file.name}</div>
            <div class="doc-meta">Uploaded just now</div>
        </div>
    `;
    
    docElement.addEventListener('click', function() {
        document.querySelectorAll('.sidebar-section:first-child .document-item').forEach(d => d.classList.remove('active'));
        this.classList.add('active');
        updateProjectIdFromDocument(this);
        saveDocumentsToStorage();
    });
    
    return docElement;
}

async function handleFileUpload(files) {
    if (files.length === 0) return;
    
    const uploadStatus = document.createElement('div');
    uploadStatus.className = 'loading active';
    uploadStatus.innerHTML = `<div class="spinner"></div><span>Uploading ${files.length} file(s)...</span>`;
    document.querySelector('.input-area').before(uploadStatus);
    
    try {
        await new Promise(resolve => setTimeout(resolve, 1500));
        
        const sidebar = document.querySelector('.sidebar-section:first-child');
        Array.from(files).forEach(file => {
            const docElement = createDocumentElement(file);
            sidebar.appendChild(docElement);
        });
        
        saveDocumentsToStorage();
        alert(`✅ Successfully uploaded ${files.length} file(s)`);
        
    } catch (error) {
        console.error('Upload error:', error);
        alert('❌ Failed to upload files. Please try again.');
    } finally {
        uploadStatus.remove();
    }
}

// ==================== DOCUMENT PERSISTENCE ====================
function saveDocumentsToStorage() {
    const documents = [];
    document.querySelectorAll('.sidebar-section:first-child .document-item').forEach(doc => {
        const name = doc.querySelector('.doc-name')?.textContent || '';
        const projectId = doc.dataset.projectId || '';
        const isActive = doc.classList.contains('active');
        documents.push({ name, projectId, isActive });
    });
    localStorage.setItem('rag_app_documents', JSON.stringify(documents));
}

function loadDocumentsFromStorage() {
    const saved = localStorage.getItem('rag_app_documents');
    if (!saved) return;
    
    try {
        const documents = JSON.parse(saved);
        const sidebar = document.querySelector('.sidebar-section:first-child');
        
        const existingDocs = sidebar.querySelectorAll('.document-item');
        existingDocs.forEach(doc => doc.remove());
        
        documents.forEach(doc => {
            const docElement = document.createElement('div');
            docElement.className = 'document-item';
            if (doc.isActive) docElement.classList.add('active');
            docElement.dataset.projectId = doc.projectId;
            
            docElement.innerHTML = `
                <div class="doc-icon">📄</div>
                <div class="doc-info">
                    <div class="doc-name">${doc.name}</div>
                    <div class="doc-meta">Uploaded</div>
                </div>
            `;
            
            docElement.addEventListener('click', function() {
                document.querySelectorAll('.sidebar-section:first-child .document-item').forEach(d => d.classList.remove('active'));
                this.classList.add('active');
                updateProjectIdFromDocument(this);
                saveDocumentsToStorage();
            });
            
            sidebar.appendChild(docElement);
        });
    } catch (e) {
        console.error('Failed to load documents:', e);
    }
}

// ==================== EVENT LISTENERS ====================
function initializeEventListeners() {
    themeToggle.addEventListener('click', () => {
        createNewChat();
    });
    
    sendBtn.addEventListener('click', sendMessage);
    
    textarea.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    textarea.addEventListener('input', resizeTextarea);
    
    suggestedQuestions.addEventListener('click', (e) => {
        const question = e.target.closest('.suggested-question');
        if (question) {
            textarea.value = question.dataset.question || question.textContent;
            resizeTextarea();
            sendMessage();
        }
    });
    
    document.querySelectorAll('.sidebar-section:first-child .document-item').forEach(doc => {
        doc.addEventListener('click', function() {
            document.querySelectorAll('.sidebar-section:first-child .document-item').forEach(d => d.classList.remove('active'));
            this.classList.add('active');
            updateProjectIdFromDocument(this);
            saveDocumentsToStorage();
        });
    });
    
    fileInput.addEventListener('change', (e) => handleFileUpload(e.target.files));
    
    // Close menus when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.chat-menu-btn') && !e.target.closest('.chat-menu-dropdown')) {
            closeAllMenus();
        }
    });
}

// ==================== INITIALIZATION ====================
function initialize() {
    initTheme();
    
    loadDocumentsFromStorage();
    loadChatsFromStorage();
    initializeEventListeners();
    resizeTextarea();
    
    if (chats.length === 0) {
        createNewChat();
    } else {
        const sortedChats = sortChats(chats);
        loadChat(sortedChats[0].id);
    }
    
    const activeDoc = document.querySelector('.sidebar-section:first-child .document-item.active');
    if (activeDoc) {
        const docName = activeDoc.querySelector('.doc-name')?.textContent || '';
        welcomeSubtitle.innerHTML = `Now viewing: <strong>${docName}</strong><br>Ask questions about this document.`;
    }
    
    console.log('✅ App initialized with chat history');
}

// Start the app
initialize();