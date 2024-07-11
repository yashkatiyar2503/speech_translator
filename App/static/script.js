$(document).ready(function() {
    $('#translateForm').on('submit', function(event) {
        event.preventDefault();
        $('#status').text('Speak now...');
        $('#originalText').text('');
        $('#translatedText').text('');

        $.ajax({
            url: '/translate',
            method: 'POST',
            data: $(this).serialize(),
            success: function(response) {
                $('#status').text('Translation completed');
                $('#originalText').text('Original: ' + response.text);
                $('#translatedText').text('Translation: ' + response.translation);
            },
            error: function(response) {
                $('#status').text('Error: ' + response.responseJSON.error);
            }
        });
    });
});