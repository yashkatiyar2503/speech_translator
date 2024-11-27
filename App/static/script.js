$(document).ready(function () {
    // Load chat history for the default language (if any)
    const selectedLanguage = $('#language').val();
    loadChatHistory(selectedLanguage);

    // Handle language selection and dynamic chat box creation
    $('#language').on('change', function () {
        const selectedLanguage = $(this).val();

        if (selectedLanguage) {
            // Show the chat container for the selected language
            const chatId = `chatContainer-${selectedLanguage}`;
            
            // Check if the chat container already exists
            if (!$(`#${chatId}`).length) {
                // If the chat container does not exist, create it
                const chatBox = `
                <div id="${chatId}" class="chat-container">
                    <!-- Chat messages for ${selectedLanguage} will appear here -->
                </div>`;
                $('#languageChats').append(chatBox);
            }

            // Hide other chat containers and show the selected one
            $('.chat-container').hide();
            $(`#${chatId}`).show();

            // Load chat history for the selected language
            loadChatHistory(selectedLanguage);
        } else {
            // Hide all chat containers if no language is selected
            $('.chat-container').hide();
        }
    });

    // Function to handle form submission and speech translation
    $('#translateForm').on('submit', function (event) {
        event.preventDefault();
        const selectedLanguage = $('#language').val();

        if (!selectedLanguage) {
            alert('Please select a language first!');
            return;
        }

        const chatId = `chatContainer-${selectedLanguage}`;
        $('#status').text('Recording speech...');

        $.ajax({
            url: '/translate',
            method: 'POST',
            data: { language: selectedLanguage },
            success: function (response) {
                $('#status').text('');

                // Append original speech (left-aligned bubble)
                const originalBubble = `
                <div class="bubble left-bubble">
                    <p class="chat-text">${response.text}</p>
                </div>`;
                $(`#${chatId}`).append(originalBubble);

                // Append translated speech (right-aligned bubble)
                const translatedBubble = `
                <div class="bubble right-bubble">
                    <p class="chat-text">${response.translation}</p>
                </div>`;
                $(`#${chatId}`).append(translatedBubble);

                // Save chat to the backend
                saveChatToBackend(response.text, response.translation, selectedLanguage);

                // Scroll to the bottom of the chat
                $(`#${chatId}`).scrollTop($(`#${chatId}`)[0].scrollHeight);
            },
            error: function (response) {
                $('#status').text('Error: ' + response.responseJSON.error);
            }
        });
    });

    // Function to load chat history for a specific language
    function loadChatHistory(language = '') {
        if (language) {
            $.ajax({
                url: '/get_chat_history',
                method: 'GET',
                data: { language: language },
                success: function (chatHistory) {
                    const chatId = `chatContainer-${language}`;
                    $(`#${chatId}`).html(chatHistory);
                    $(`#${chatId}`).scrollTop($(`#${chatId}`)[0].scrollHeight); // Scroll to bottom after loading history
                },
                error: function () {
                    $(`#chatContainer-${language}`).html('<p class="error-text">Failed to load chat history.</p>');
                }
            });
        }
    }

    // Function to save chat bubbles to the backend
    function saveChatToBackend(originalText, translatedText, language) {
        $.ajax({
            url: '/save_chat',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                original_text: originalText,
                translated_text: translatedText,
                language: language
            }),
            success: function () {
                console.log('Chat saved successfully!');
            },
            error: function () {
                console.error('Failed to save chat.');
            }
        });
    }

    // Clear chat history for the selected language when the Clear Chat button is clicked
    $('#clearChatButton').on('click', function () {
        const selectedLanguage = $('#language').val();

        if (!selectedLanguage) {
            alert('Please select a language first!');
            return;
        }

        console.log("Request to clear chat for language:", selectedLanguage); // Debug selected language

        const chatId = `chatContainer-${selectedLanguage}`;

        $.ajax({
            url: '/clear_chat_history',
            method: 'POST',
            contentType: 'application/json', // Ensure correct content type for sending JSON
            data: JSON.stringify({ language: selectedLanguage }), // Send data as JSON
            success: function () {
                console.log('Chat history cleared for ' + selectedLanguage);
                $(`#${chatId}`).empty(); // Clear only the selected language's chat container
            },
            error: function (xhr, status, error) {
                console.error('Failed to clear chat history:', xhr.responseText); // Debug error response
                alert('Failed to clear chat history. Please try again.');
            }
        });
    });
});
