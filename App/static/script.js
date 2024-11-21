$(document).ready(function() {
    // Load chat history from the backend for the logged-in user
    loadChatHistory();

    // Function to handle form submission and speech translation
    $('#translateForm').on('submit', function(event) {
        event.preventDefault();
        $('#status').text('Recording speech...');
        $('#originalText').text('');
        $('#translatedText').text('');

        $.ajax({
            url: '/translate',
            method: 'POST',
            data: $(this).serialize(),
            success: function(response) {
                $('#status').text('');

                // Append original speech (left-aligned bubble)
                var originalBubble = '<div class="bubble left-bubble">' +
                                     '<p class="chat-text">' + response.text + '</p>' +
                                     '</div>';
                $('#chatContainer').append(originalBubble);

                // Append translated speech (right-aligned bubble)
                var translatedBubble = '<div class="bubble right-bubble">' +
                                       '<p class="chat-text">' + response.translation + '</p>' +
                                       '</div>';
                $('#chatContainer').append(translatedBubble);

                // Save chat to the backend
                saveChatToBackend(response.text, response.translation);

                // Scroll to the bottom of the chat
                $('#chatContainer').scrollTop($('#chatContainer')[0].scrollHeight);
            },
            error: function(response) {
                $('#status').text('Error: ' + response.responseJSON.error);
            }
        });
    });

    // Function to load chat history from the backend
    function loadChatHistory() {
        $.ajax({
            url: '/get_chat_history',
            method: 'GET',
            success: function(chatHistory) {
                $('#chatContainer').html(chatHistory);
                $('#chatContainer').scrollTop($('#chatContainer')[0].scrollHeight); // Scroll to bottom after loading history
            },
            error: function() {
                $('#chatContainer').html('<p class="error-text">Failed to load chat history.</p>');
            }
        });
    }

    // Function to save chat bubbles to the backend
    function saveChatToBackend(originalText, translatedText) {
        $.ajax({
            url: '/save_chat',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                original_text: originalText,
                translated_text: translatedText
            }),
            success: function() {
                console.log('Chat saved successfully!');
            },
            error: function() {
                console.error('Failed to save chat.');
            }
        });
    }

    // Clear chat history for the user when the Clear Chat button is clicked
    $('#clearChatButton').on('click', function() {
        $.ajax({
            url: '/clear_chat_history',
            method: 'POST',
            success: function() {
                $('#chatContainer').empty();
                console.log('Chat history cleared.');
            },
            error: function() {
                console.error('Failed to clear chat history.');
            }
        });
    });
});
