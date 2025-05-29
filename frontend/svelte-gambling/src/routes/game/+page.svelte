<script>
  import { onMount } from 'svelte';
</script>

<div class="flex flex-col items-center justify-center h-full space-y-6">
  <h2 class="text-2xl font-semibold text-purple-300 mb-2">Now Playing</h2>
  <div class="w-[1000px] h-[562px] border border-gray-700 rounded-2xl overflow-hidden shadow-xl">
    <iframe
      src="/testgame/testgame.html"
      title="Godot Game"
      class="w-full h-full rounded-2xl"
      style="border: none;"
      allow="fullscreen"
    ></iframe>
  </div>
</div>
