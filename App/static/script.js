$(document).ready(function() {
    // Load chat history from localStorage
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
                $('#status').text('Translation completed');

                // Append original speech (left-aligned bubble)
                var originalBubble = '<div class="bubble left-bubble">' +
                                     '<p class="chat-text">' + response.text + '</p>' +
                                     '</div>';
                $('#chatContainer').append(originalBubble);

                // Append translated speech (right-aligned bubble)
                var translatedBubble = '<div class="bubble right-bubble">' +
                                       '<p class="chat-text">Translation: ' + response.translation + '</p>' +
                                       '</div>';
                $('#chatContainer').append(translatedBubble);

                // Save chat to localStorage
                saveChatToLocalStorage(originalBubble, translatedBubble);

                // Scroll to the bottom of the chat
                $('#chatContainer').scrollTop($('#chatContainer')[0].scrollHeight);
            },
            error: function(response) {
                $('#status').text('Error: ' + response.responseJSON.error);
            }
        });
    });

    // Function to load chat history from localStorage
    function loadChatHistory() {
        var chatHistory = localStorage.getItem('chatHistory');
        if (chatHistory) {
            $('#chatContainer').html(chatHistory);
            $('#chatContainer').scrollTop($('#chatContainer')[0].scrollHeight); // Scroll to bottom after loading history
        }
    }

    // Function to save chat bubbles to localStorage
    function saveChatToLocalStorage(originalBubble, translatedBubble) {
        var chatHistory = localStorage.getItem('chatHistory') || '';
        chatHistory += originalBubble + translatedBubble;
        localStorage.setItem('chatHistory', chatHistory);
    }

    // Clear chat history when the Clear Chat button is clicked
    $('#clearChatButton').on('click', function() {
        localStorage.removeItem('chatHistory');
        $('#chatContainer').empty();
    });
});
