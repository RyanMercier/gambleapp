const API_BASE_URL = 'http://localhost:8000';

// Global error handlers
const errorHandlers = {
  401: (error) => {
    // Token expired or invalid - clean up and redirect
    console.warn('🔐 Authentication expired');
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    
    // Only redirect if we're not already on a public page
    const currentPath = window.location.pathname;
    const publicPaths = ['/', '/login'];
    if (!publicPaths.includes(currentPath)) {
      window.location.href = '/login';
    }
    
    throw new Error('Session expired. Please log in again.');
  },
  403: (error) => {
    throw new Error('Access denied. You don\'t have permission for this action.');
  },
  404: (error) => {
    throw new Error('The requested resource was not found.');
  },
  429: (error) => {
    throw new Error('Too many requests. Please wait a moment and try again.');
  },
  500: (error) => {
    throw new Error('Server error. Please try again later.');
  },
  503: (error) => {
    throw new Error('Service temporarily unavailable. Please try again later.');
  }
};

async function apiFetch(endpoint, options = {}) {
  const token = localStorage.getItem('token');
  
  const config = {
    method: 'GET',
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    },
  };

  try {
    console.log(`🌐 API ${config.method}: ${endpoint}`);
    
    const response = await fetch(`${API_BASE_URL}${endpoint}`, config);
    
    // Handle specific HTTP status codes
    if (!response.ok) {
      const errorHandler = errorHandlers[response.status];
      if (errorHandler) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        errorHandler(errorData);
      } else {
        // Generic error handling
        const error = await response.json().catch(() => ({ detail: `HTTP ${response.status}: ${response.statusText}` }));
        throw new Error(error.detail || `Request failed with status ${response.status}`);
      }
    }

    const data = await response.json();
    console.log(`✅ API Success: ${endpoint}`);
    return data;
    
  } catch (error) {
    console.error(`❌ API Error (${endpoint}):`, error.message);
    
    // Handle network errors
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      throw new Error('Unable to connect to server. Please check your internet connection.');
    }
    
    // Handle timeout errors
    if (error.name === 'AbortError') {
      throw new Error('Request timed out. Please try again.');
    }
    
    // Re-throw the error for the caller to handle
    throw error;
  }
}

// Specialized API functions with built-in error handling

export async function authenticateUser(credentials, isLogin = true) {
  try {
    const endpoint = isLogin ? '/auth/login' : '/auth/register';
    const data = await apiFetch(endpoint, {
      method: 'POST',
      body: JSON.stringify(credentials)
    });

    if (!data?.token || !data?.user) {
      throw new Error('Incomplete response from server');
    }

    // Store authentication data
    localStorage.setItem('token', data.token);
    localStorage.setItem('user', JSON.stringify(data.user));
    
    console.log('✅ Authentication successful');
    return data;
    
  } catch (error) {
    console.error('❌ Authentication failed:', error);
    throw error;
  }
}

export async function validateSession() {
  try {
    const user = await apiFetch('/auth/me');
    
    // Update stored user data
    localStorage.setItem('user', JSON.stringify(user));
    
    return user;
  } catch (error) {
    // Session validation failed - clear stored data
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    throw error;
  }
}

export async function searchAttentionTarget(query, targetType = 'politician') {
  try {
    return await apiFetch('/search', {
      method: 'POST',
      body: JSON.stringify({
        query: query.trim(),
        target_type: targetType
      })
    });
  } catch (error) {
    console.error('Search failed:', error);
    throw new Error(`Search failed: ${error.message}`);
  }
}

export async function getChartData(targetId, days = 30) {
  try {
    return await apiFetch(`/targets/${targetId}/chart?days=${days}`);
  } catch (error) {
    console.error('Chart data fetch failed:', error);
    throw new Error(`Failed to load chart data: ${error.message}`);
  }
}

export async function getTargets(targetType = null, limit = 50) {
  try {
    const params = new URLSearchParams();
    if (targetType) params.append('target_type', targetType);
    if (limit) params.append('limit', limit.toString());
    
    const query = params.toString() ? `?${params.toString()}` : '';
    return await apiFetch(`/targets${query}`);
  } catch (error) {
    console.error('Targets fetch failed:', error);
    throw new Error(`Failed to load targets: ${error.message}`);
  }
}

export async function executeTrade(targetId, tradeType, shares) {
  try {
    return await apiFetch('/trade', {
      method: 'POST',
      body: JSON.stringify({
        target_id: targetId,
        trade_type: tradeType,
        shares: parseFloat(shares)
      })
    });
  } catch (error) {
    console.error('Trade execution failed:', error);
    throw new Error(`Trade failed: ${error.message}`);
  }
}

export async function getPortfolio() {
  try {
    return await apiFetch('/portfolio');
  } catch (error) {
    console.error('Portfolio fetch failed:', error);
    throw new Error(`Failed to load portfolio: ${error.message}`);
  }
}

export async function getTournaments() {
  try {
    return await apiFetch('/tournaments');
  } catch (error) {
    console.error('Tournaments fetch failed:', error);
    throw new Error(`Failed to load tournaments: ${error.message}`);
  }
}

export async function joinTournament(tournamentId) {
  try {
    return await apiFetch('/tournaments/join', {
      method: 'POST',
      body: JSON.stringify({
        tournament_id: tournamentId
      })
    });
  } catch (error) {
    console.error('Tournament join failed:', error);
    throw new Error(`Failed to join tournament: ${error.message}`);
  }
}

// Utility functions
export function formatCurrency(amount) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(amount);
}

export function formatNumber(num, decimals = 1) {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  }).format(num);
}

export function formatDate(dateString) {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
}

export function formatDateTime(dateString) {
  return new Date(dateString).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

export function getTypeIcon(type) {
  const icons = {
    politician: '🏛️',
    billionaire: '💰',
    country: '🌍',
    stock: '📈'
  };
  return icons[type] || '📊';
}

export function getPerformanceColor(value) {
  if (value > 0) return 'text-emerald-400';
  if (value < 0) return 'text-red-400';
  return 'text-gray-400';
}

// Default export
export default apiFetch;