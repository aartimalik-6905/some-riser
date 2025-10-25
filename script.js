// Wait for the page to load
document.addEventListener('DOMContentLoaded', () => {

    // --- 1. Basic UI (Splash, Contact, Dark Mode) ---
    const splashScreen = document.getElementById('splash-screen');
    if (splashScreen) {
        setTimeout(() => {
            splashScreen.classList.add('hidden');
        }, 2000);
    }

    const contactBtn = document.getElementById('contact-btn');
    if (contactBtn) {
        contactBtn.addEventListener('click', (event) => {
            event.preventDefault();
            alert('contact malikaarti6905@gmail.com for more queries');
        });
    }

    const toggleBtn = document.getElementById('dark-mode-toggle');
    const body = document.body;
    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            body.classList.toggle('dark-mode');
            toggleBtn.textContent = body.classList.contains('dark-mode') ? '☀️' : '🌙';
        });
    }

    // --- 2. Get All the NEW Elements ---
    // This is the clean, correct list with NO duplicates
    const browseBtn = document.getElementById('browse-btn');
    const fileInput = document.getElementById('file-input');
    const fileNameDisplay = document.getElementById('file-name-display');
    const analyzeTextBtn = document.getElementById('analyze-text-btn');
    const textInput = document.getElementById('text-input');

    // Result display areas
    const resultsDemoText = document.getElementById('results-demo-text');
    const summaryBox = document.getElementById('summary-box');
    const keywordsBox = document.getElementById('keywords-box');
    const tableBox = document.getElementById('table-box');
    
    // Result content holders
    const summaryOverview = document.getElementById('summary-overview');
    const summaryInsights = document.getElementById('summary-insights');
    const keywordsList = document.getElementById('keywords-list');
    const tableHeader = document.getElementById('table-header-row');
    const tableSampleRow = document.getElementById('table-sample-row');
    const tableInsights = document.getElementById('table-insights');
    const summarySubheading = document.getElementById('summary-subheading'); // For image count

    // The URL of our Python server
    const API_URL = 'http://127.0.0.1:5000';

    // --- 3. Wire Up the Buttons ---

    // When "Browse Files" is clicked, trigger the hidden file input
    browseBtn.addEventListener('click', () => {
        fileInput.click();
    });

    // === THIS IS THE FINAL, COMPLETE FILE HANDLER ===
    fileInput.addEventListener('change', () => {
        const file = fileInput.files[0];
        if (!file) return;

        fileNameDisplay.textContent = `Selected: ${file.name}`;
        
        const fileName = file.name.toLowerCase();

        if (fileName.endsWith('.csv')) {
            // --- CSV Logic ---
            const reader = new FileReader();
            reader.readAsText(file);
            reader.onload = () => {
                hideAllResults();
                tableBox.style.display = 'block';
                analyzeTable(reader.result);
            };

        } else if (fileName.endsWith('.txt')) {
            // --- TXT Logic ---
            const reader = new FileReader();
            reader.readAsText(file);
            reader.onload = () => {
                hideAllResults();
                summaryBox.style.display = 'block';
                keywordsBox.style.display = 'block';
                analyzeDocument(reader.result);
            };

        } else if (fileName.endsWith('.png') || fileName.endsWith('.jpg') || fileName.endsWith('.jpeg')) {
            // --- IMAGE Logic ---
            hideAllResults();
            analyzeImage(file); // This will call displayMixedResults

        } else if (fileName.endsWith('.pdf') || fileName.endsWith('.docx')) {
            // --- NEW MIXED DOC Logic ---
            analyzeMixedDoc(file); // This will call displayMixedResults
        
        } else {
            alert("Unsupported file type!");
        }
    });
    // === END OF FINAL FILE HANDLER ===

    // When "Analyze Pasted Text" is clicked...
    analyzeTextBtn.addEventListener('click', () => {
        const text = textInput.value;
        if (text.trim() === '') {
            alert('Please paste some text to analyze.');
            return;
        }
        // Assume pasted text is a document
        hideAllResults();
        summaryBox.style.display = 'block';
        keywordsBox.style.display = 'block';
        analyzeDocument(text);
    });

    // --- 4. API "fetch" Functions ---
    // These functions talk to your Python server

    function analyzeDocument(text) {
        showLoading(true);
        fetch(`${API_URL}/summarize-doc`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ text: text })
        })
        .then(response => response.json())
        .then(data => {
            showLoading(false);
            // --- THIS IS THE FIX ---
            // .txt and pasted text ONLY return doc data.
            displayDocResults(data); 
        })
        .catch(error => {
            console.error('Error:', error);
            showLoading(false);
            alert('Error connecting to server. Is app.py running?');
        });
    }

    function analyzeTable(text) {
        showLoading(true);
        fetch(`${API_URL}/summarize-table`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ text: text })
        })
        .then(response => response.json())
        .then(data => {
            showLoading(false);
            if (data.error) {
                alert(`Error: ${data.error}`);
            } else {
                displayTableResults(data);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showLoading(false);
            alert('Error connecting to server. Is app.py running?');
        });
    }

    function analyzeImage(imageFile) {
        showLoading(true);
        
        const formData = new FormData();
        formData.append('image', imageFile);

        fetch(`${API_URL}/summarize-image`, {
            method: 'POST',
            body: formData 
        })
        .then(response => response.json())
        .then(data => {
            showLoading(false);
            if (data.error) {
                alert(`Error: ${data.error}`);
            } else {
                // --- THIS IS THE FIX ---
                // The image handler on the backend returns a *mixed* result
                displayMixedResults(data); 
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showLoading(false);
            alert('Error connecting to server. Is app.py running?');
        });
    }

    function analyzeMixedDoc(docFile) {
        showLoading(true);

        const formData = new FormData();
        formData.append('doc', docFile); 

        fetch(`${API_URL}/summarize-mixed-doc`, {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            showLoading(false);
            if (data.error) {
                alert(`Error: ${data.error}`);
            } else {
                // PDF/DOCX handler returns a mixed result
                displayMixedResults(data);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showLoading(false);
            alert('Error connecting to server. Is app.py running?');
        });
    }

    // --- 5. Display Functions ---
    // These functions update the HTML with the results

    function displayDocResults(data) {
        // Clear old results
        keywordsList.innerHTML = '';
        summaryInsights.innerHTML = '';

        // Add keywords
        if(data.keywords) {
            data.keywords.forEach(keyword => {
                const el = document.createElement('span');
                el.className = 'keyword';
                el.textContent = keyword;
                keywordsList.appendChild(el);
            });
        }

        // Add entities
        if(data.entities) {
            data.entities.forEach(entity => {
                const el = document.createElement('li');
                el.textContent = entity;
                summaryInsights.appendChild(el);
            });
        }
        
        // Add the main summary text
        summaryOverview.textContent = data.summary || "Summary could not be generated.";

        // --- Add Image Count ---
        if (data.image_count !== undefined && data.image_count > 0) {
            summarySubheading.textContent = `Found ${data.image_count} image(s) in this document.`;
        } else {
            // Reset to default
            summarySubheading.textContent = 'AI-generated document overview';
        }
    }
    
    function displayTableResults(data) {
        // Clear old results
        tableHeader.innerHTML = '';
        tableSampleRow.innerHTML = '';
        tableInsights.innerHTML = '';

        // Add table headers
        if(data.columns) {
            data.columns.forEach(col => {
                const el = document.createElement('th');
                el.textContent = col;
                tableHeader.appendChild(el);
            });
        }
        
        // Add sample row data
        if(data.sample_row && data.columns) {
            data.columns.forEach(col => {
                const el = document.createElement('td');
                el.textContent = data.sample_row[col] || '';
                tableSampleRow.appendChild(el);
            });
        }

        // Add insights
        if(data.insights) {
            data.insights.forEach(insight => {
                const el = document.createElement('li');
                el.textContent = insight;
                tableInsights.appendChild(el);
            });
        }
    }

    function displayMixedResults(data) {
        // Clear all old results
        hideAllResults();

        // Show all three result boxes
        resultsDemoText.style.display = 'none';
        summaryBox.style.display = 'block';
        keywordsBox.style.display = 'block';
        tableBox.style.display = 'block';

        // 1. Fill the Doc Summary and Keyword boxes
        if (data.doc_summary) {
            displayDocResults(data.doc_summary);
        }

        // 2. Fill the Table Insights box
        if (data.table_summary && !data.table_summary.error) {
            displayTableResults(data.table_summary);
        } else if (data.table_summary && data.table_summary.error) {
            // Show the "No tables found" error
            tableInsights.innerHTML = `<li>${data.table_summary.error}</li>`;
        }
    }
    
    function hideAllResults() {
        // Hide the demo text
        resultsDemoText.style.display = 'none';
        // Hide all result boxes
        summaryBox.style.display = 'none';
        keywordsBox.style.display = 'none';
        tableBox.style.display = 'none';
    }
    
    function showLoading(isLoading) {
        document.getElementById('results-title').textContent = isLoading 
            ? 'Analyzing... ✨' 
            : 'Preview Results';
    }
    
    // Hide all results on initial load
    hideAllResults();
    
});