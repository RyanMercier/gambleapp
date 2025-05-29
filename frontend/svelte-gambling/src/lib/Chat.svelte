<script>
  import { onMount } from 'svelte';
  let socket;
  let messages = [];
  let input = '';

  onMount(() => {
    socket = new WebSocket('ws://localhost:8000/ws/chat');
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      messages = [...messages, data];
    };
  });

  function sendMessage() {
    if (input.trim()) {
      const user = JSON.parse(localStorage.getItem("user"));
      const payload = {
        username: user?.username || "Anon",
        message: input.trim()
      };
      socket.send(JSON.stringify(payload));
      input = '';
    }
  }
</script>

<div class="flex flex-col h-full">
  <div class="flex-1 overflow-y-auto space-y-2 pr-2">
    {#each messages as { username, message }}
      <div class="text-sm">
        <span class="text-purple-400 font-semibold">{username}:</span>
        <span class="ml-2">{message}</span>
      </div>
    {/each}
  </div>

  <div class="mt-4 flex gap-2">
    <input
      bind:value={input}
      type="text"
      placeholder="Type a message..."
      class="flex-1 p-2 rounded-md bg-[#2a2a2e] text-white border border-gray-600 outline-none"
      on:keydown={(e) => e.key === 'Enter' && sendMessage()}
    />
    <button
      on:click={sendMessage}
      class="px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-md text-white"
    >
      Send
    </button>
  </div>
</div>
