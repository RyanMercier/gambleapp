<script>
  import { onMount, onDestroy } from 'svelte';
  import { user } from '$lib/stores';
  import apiFetch from '$lib/api';

  let messages = [];
  let newMessage = '';
  let messagesContainer;
  let ws = null;
  let connectionStatus = 'disconnected';
  let pollInterval;

  onMount(async () => {
    if ($user) {
      await loadRecentMessages();
      connectWebSocket();
      // Poll for new messages every 3 seconds as fallback
      pollInterval = setInterval(loadRecentMessages, 3000);
    }
  });

  onDestroy(() => {
    if (ws) {
      ws.close();
    }
    if (pollInterval) {
      clearInterval(pollInterval);
    }
  });

  async function loadRecentMessages() {
    try {
      const response = await apiFetch('/chat/messages?limit=50');
      messages = response.messages || [];
      scrollToBottom();
    } catch (error) {
      console.error('Failed to load chat messages:', error);
    }
  }

  function connectWebSocket() {
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/chat`;

      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        connectionStatus = 'connected';
        console.log('Chat WebSocket connected');
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'chat_message') {
          const message = data.message;
          messages = [...messages, message];
          scrollToBottom();
        }
      };

      ws.onclose = () => {
        connectionStatus = 'disconnected';
        console.log('Chat WebSocket disconnected - using polling fallback');
      };

      ws.onerror = (error) => {
        console.error('Chat WebSocket error:', error);
        connectionStatus = 'disconnected';
        console.log('WebSocket failed - using polling fallback');
      };
    } catch (error) {
      console.error('Failed to connect to chat WebSocket:', error);
      connectionStatus = 'disconnected';
      console.log('WebSocket connection failed - using polling fallback');
    }
  }

  async function sendMessage() {
    if (!newMessage.trim() || !$user) return;

    try {
      const message = {
        content: newMessage.trim(),
        timestamp: new Date().toISOString()
      };

      await apiFetch('/chat/send', {
        method: 'POST',
        body: JSON.stringify(message)
      });

      newMessage = '';
      // Reload messages immediately after sending
      await loadRecentMessages();
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  }


  function scrollToBottom() {
    if (messagesContainer) {
      setTimeout(() => {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
      }, 50);
    }
  }

  function formatTime(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
  }



  function handleKeydown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  }

  // Watch for user changes
  $: if ($user && connectionStatus === 'disconnected') {
    connectWebSocket();
  }
</script>

{#if $user}
  <!-- Global Chat Panel - Fixed Right Side -->
  <div class="fixed top-16 right-0 w-1/5 bottom-0 bg-gray-900 border-l border-gray-700 flex flex-col z-40">
    <!-- Chat Header -->
    <div class="bg-gray-800 p-2 border-b border-gray-700">
      <div class="flex items-center gap-2">
        <div class="w-2 h-2 rounded-full {connectionStatus === 'connected' ? 'bg-green-400' : connectionStatus === 'error' ? 'bg-red-400' : 'bg-yellow-400'}"></div>
        <span class="text-xs font-semibold text-white">Global Chat</span>
        <span class="text-xs text-gray-500">({messages.length})</span>
      </div>
    </div>

    <!-- Messages Area -->
    <div
      bind:this={messagesContainer}
      class="flex-1 overflow-y-auto p-2 space-y-1"
    >
      {#if messages.length === 0}
        <div class="text-center text-gray-500 py-4">
          <p class="text-xs">No messages yet</p>
          <p class="text-xs opacity-75">Start a conversation!</p>
        </div>
      {:else}
        {#each messages as message}
          <div class="text-xs">
            <span class="text-gray-400">{formatTime(message.timestamp)}</span>
            <span class="text-blue-400 font-medium">{message.username}:</span>
            <span class="text-gray-200">{message.content}</span>
          </div>
        {/each}
      {/if}
    </div>

    <!-- Message Input -->
    <div class="border-t border-gray-700 p-2">
      <div class="flex gap-1">
        <input
          bind:value={newMessage}
          on:keydown={handleKeydown}
          placeholder="Type message..."
          class="flex-1 bg-gray-800 text-white placeholder-gray-500 border border-gray-600 rounded px-2 py-1 text-xs focus:outline-none focus:border-blue-500"
          maxlength="500"
          disabled={false}
        />
        <button
          on:click={sendMessage}
          disabled={!newMessage.trim()}
          class="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded px-2 py-1 text-xs"
          title="Send"
        >
          →
        </button>
      </div>
      {#if connectionStatus !== 'connected'}
        <div class="text-xs text-gray-500 mt-1">
          {connectionStatus === 'error' ? 'Connection error' : 'Connecting...'}
        </div>
      {/if}
    </div>
  </div>
{/if}

