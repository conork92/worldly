// Example: How to include API key in requests from frontend
// 
// For POST/PATCH requests that modify data, include the X-API-Key header:
//
// Example 1: Creating a quote
fetch('http://localhost:8000/api/quotes', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-API-Key': 'your-api-key-here'  // Add this header
    },
    body: JSON.stringify({
        quote: "Your quote here",
        author: "Author Name",
        // ... other fields
    })
})
.then(response => response.json())
.then(data => console.log(data))
.catch(error => console.error('Error:', error));

//
// Example 2: Updating a book
fetch('http://localhost:8000/api/books/123', {
    method: 'PATCH',
    headers: {
        'Content-Type': 'application/json',
        'X-API-Key': 'your-api-key-here'  // Add this header
    },
    body: JSON.stringify({
        country: "Nigeria",
        iso_code_3: "NGA"
    })
})
.then(response => response.json())
.then(data => console.log(data))
.catch(error => console.error('Error:', error));

//
// Example 3: Updating an album
fetch('http://localhost:8000/api/albums/listened/456', {
    method: 'PATCH',
    headers: {
        'Content-Type': 'application/json',
        'X-API-Key': 'your-api-key-here'  // Add this header
    },
    body: JSON.stringify({
        listen_date: "2024-01-15",
        rating: 8,
        comments: "Great album!"
    })
})
.then(response => response.json())
.then(data => console.log(data))
.catch(error => console.error('Error:', error));

