const { Room } = require("colyseus");
const { Schema, MapSchema } = require("@colyseus/schema");

class ChatUser extends Schema {
  constructor() {
    super();
    this.username = "";
    this.joinedAt = Date.now();
    this.messageCount = 0;
  }
}
ChatUser.schema = {
  username: "string",
  joinedAt: "number",
  messageCount: "number"
};

class GlobalChatState extends Schema {
  constructor() {
    super();
    this.users = new MapSchema();
    this.totalMessages = 0;
  }
}
GlobalChatState.schema = {
  users: { map: ChatUser },
  totalMessages: "number"
};

class GlobalChatRoom extends Room {
  onCreate(options) {
    this.setState(new GlobalChatState());
    
    // Store recent messages in memory (not in state to save bandwidth)
    this.recentMessages = [];
    this.maxRecentMessages = 50;
    
    // Message rate limiting
    this.messageRateLimit = new Map();
    this.maxMessagesPerMinute = 10;
    
    console.log("🌍 Global chat room created");
    
    this.onMessage("chat_message", (client, message) => {
      this.handleChatMessage(client, message);
    });
  }
  
  onJoin(client, options) {
    console.log(`👤 User joining global chat: ${options.username}`);
    
    const user = new ChatUser();
    user.username = options.username || `Player${client.sessionId.slice(0, 4)}`;
    user.joinedAt = Date.now();
    
    this.state.users.set(client.sessionId, user);
    
    // Send recent message history to new user
    this.recentMessages.slice(-20).forEach(msg => {
      client.send("chat_message", msg);
    });
    
    // Notify others
    this.broadcast("user_joined", {
      username: user.username,
      timestamp: Date.now()
    }, { except: client });
    
    console.log(`✅ ${user.username} joined global chat. Total users: ${this.state.users.size}`);
  }
  
  handleChatMessage(client, message) {
    const user = this.state.users.get(client.sessionId);
    if (!user || !message || !message.text) return;
    
    // Rate limiting
    if (!this.checkRateLimit(client.sessionId)) {
      client.send("error", { message: "You're sending messages too quickly. Please slow down." });
      return;
    }
    
    // Validate message
    const text = message.text.trim();
    if (text.length === 0 || text.length > 500) {
      client.send("error", { message: "Message must be between 1 and 500 characters." });
      return;
    }
    
    // Create message object
    const chatMessage = {
      username: user.username,
      message: text,
      timestamp: Date.now()
    };
    
    // Store in recent messages
    this.recentMessages.push(chatMessage);
    if (this.recentMessages.length > this.maxRecentMessages) {
      this.recentMessages.shift();
    }
    
    // Update stats
    user.messageCount++;
    this.state.totalMessages++;
    
    // Broadcast to all users
    this.broadcast("chat_message", chatMessage);
    
    console.log(`💬 ${user.username}: ${text}`);
  }
  
  checkRateLimit(sessionId) {
    const now = Date.now();
    const userRateLimit = this.messageRateLimit.get(sessionId) || [];
    
    // Remove old timestamps (older than 1 minute)
    const recentTimestamps = userRateLimit.filter(timestamp => now - timestamp < 60000);
    
    if (recentTimestamps.length >= this.maxMessagesPerMinute) {
      return false;
    }
    
    recentTimestamps.push(now);
    this.messageRateLimit.set(sessionId, recentTimestamps);
    
    return true;
  }
  
  onLeave(client, consented) {
    const user = this.state.users.get(client.sessionId);
    if (user) {
      console.log(`👋 ${user.username} left global chat`);
      
      // Notify others
      this.broadcast("user_left", {
        username: user.username,
        timestamp: Date.now()
      }, { except: client });
      
      this.state.users.delete(client.sessionId);
      this.messageRateLimit.delete(client.sessionId);
    }
  }
  
  onDispose() {
    console.log("🔚 Global chat room disposed");
  }
}

module.exports = GlobalChatRoom;