<script>
  export let size = 'md';
  export let color = 'blue';
  
  const sizes = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12'
  };
  
  const colors = {
    blue: 'border-blue-400/30 border-t-blue-400',
    white: 'border-white/30 border-t-white',
    gray: 'border-gray-400/30 border-t-gray-400'
  };
</script>

<div class="flex items-center justify-center">
  <div class="{sizes[size]} border-2 {colors[color]} rounded-full animate-spin"></div>
</div>