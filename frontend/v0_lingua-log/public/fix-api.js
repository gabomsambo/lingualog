// Fix API URLs for Docker networking
// This script intercepts fetch requests and fixes URLs to work with Docker networking

// Store the original fetch function
const originalFetch = window.fetch;

// Override the fetch function
window.fetch = function(url, options) {
  // Only modify if it's a string URL
  if (typeof url === 'string') {
    // Replace api:8000 with localhost:8000
    const newUrl = url.replace('api:8000', 'localhost:8000');
    
    // For debugging - log the transformation
    console.log(`API URL transformed: ${url} -> ${newUrl}`);
    
    // Call the original fetch with the modified URL
    return originalFetch(newUrl, options);
  }
  
  // If not a string or doesn't need modification, just pass through
  return originalFetch(url, options);
};

console.log('API URL fix script loaded'); 