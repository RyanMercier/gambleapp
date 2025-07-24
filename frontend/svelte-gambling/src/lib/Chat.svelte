<script>
  export let messages = [];
  export let onSendMessage; // Direct callback from parent
  export let disabled = false;
  export let placeholder = "Type a message...";
  
  let newMessage = "";
  let chatContainer;
  
  // Auto-scroll to bottom when new messages arrive
  $: if (chatContainer && messages.length > 0) {
    setTimeout(() => {
      chatContainer.scrollTop = chatContainer.scrollHeight;
    }, 50);
  }
  
  function handleSendMessage() {
    if (!newMessage.trim() || disabled || !onSendMessage) return;
    
    const message = newMessage.trim();
    newMessage = "";
    
    console.log("📤 Chat component sending message:", message);
    
    // Call the parent's callback directly
    onSendMessage(message);
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
  <!-- Messages Container -->
  <div 
    class="flex-1 overflow-y-auto p-2 space-y-1" 
    bind:this={chatContainer}
  >
    {#each messages as message}
      {#if message.isSystem}
        <!-- System Messages -->
        <div class="text-center py-1">
          <span class="text-xs text-gray-500 italic">
            {message.message}
          </span>
        </div>
      {:else}
        <!-- Regular Chat Messages -->
        <div class="flex items-start gap-2 py-1 px-2 rounded hover:bg-white/5 transition-colors {message.isOwn ? 'bg-purple-500/10' : ''}">
          <!-- Username and Timestamp (Left) -->
          <div class="flex-shrink-0 min-w-0 w-20">
            <div class="text-xs font-medium {message.isOwn ? 'text-purple-300' : 'text-blue-300'} truncate">
              {message.isOwn ? 'You' : message.username}
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
      {/if}
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
        class="input flex-1 text-sm py-2 px-3 {disabled ? 'opacity-50' : ''}"
        bind:value={newMessage}
        on:keydown={handleKeyPress}
        {disabled}
      />
      <button 
        class="btn btn-primary px-4 py-2 text-sm {disabled ? 'opacity-50' : ''}"
        on:click={handleSendMessage}
        disabled={!newMessage.trim() || disabled || !onSendMessage}
      >
        Send
      </button>
    </div>
    
    {#if disabled}
      <div class="text-xs text-gray-500 mt-1 text-center">
        Chat unavailable - connection lost
      </div>
    {:else if !onSendMessage}
      <div class="text-xs text-gray-500 mt-1 text-center">
        Chat handler not ready
      </div>
    {/if}
  </div>
</div>