<script>
  export let messages = [];
  export let newMessage = "";
  export let onSendMessage;
  export let disabled = false;
  export let placeholder = "Type a message...";
  
  let chatContainer;
  
  // Auto-scroll to bottom when new messages arrive
  $: if (chatContainer && messages.length > 0) {
    setTimeout(() => {
      chatContainer.scrollTop = chatContainer.scrollHeight;
    }, 50);
  }
  
  function handleSendMessage() {
    if (newMessage.trim() && onSendMessage && !disabled) {
      onSendMessage(newMessage.trim());
      newMessage = "";
    }
  }
  
  function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSendMessage();
    }
  }
  
  function formatTime(timestamp) {
    return new Date(timestamp).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  }
</script>

<div class="flex flex-col h-full">
  <!-- Chat Header -->
  <div class="p-4 border-b border-white/10">
    <h3 class="font-semibold">Chat</h3>
  </div>
  
  <!-- Messages Container -->
  <div 
    class="flex-1 overflow-y-auto p-2 space-y-1" 
    bind:this={chatContainer}
  >
    {#each messages as message}
      <div class="flex items-start gap-2 py-1 px-2 rounded hover:bg-white/5 transition-colors">
        <!-- Username and Timestamp (Left) -->
        <div class="flex-shrink-0 min-w-0 w-20">
          <div class="text-xs font-medium text-purple-400 truncate">
            {message.username}
          </div>
          <div class="text-xs text-gray-500 leading-none">
            {formatTime(message.timestamp)}
          </div>
        </div>
        
        <!-- Message Content (Right) -->
        <div class="flex-1 min-w-0">
          <div class="text-sm text-gray-200 break-words leading-tight">
            {message.message}
          </div>
        </div>
      </div>
    {/each}
    
    {#if messages.length === 0}
      <div class="text-center text-gray-400 py-8">
        <div class="text-2xl mb-2">💬</div>
        <div class="text-sm">No messages yet</div>
        <div class="text-xs">Start the conversation!</div>
      </div>
    {/if}
  </div>
  
  <!-- Input Area -->
  <div class="p-2 border-t border-white/10">
    <div class="flex gap-2">
      <input
        type="text"
        {placeholder}
        class="input flex-1 text-sm py-2 px-3"
        bind:value={newMessage}
        on:keydown={handleKeyPress}
        {disabled}
      />
      <button 
        class="btn btn-primary px-4 py-2 text-sm"
        on:click={handleSendMessage}
        disabled={!newMessage.trim() || disabled}
      >
        Send
      </button>
    </div>
  </div>
</div>