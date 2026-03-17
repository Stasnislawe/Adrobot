$(document).ready(function() {
    if (typeof campaignId === 'undefined') return;

    // Функция получения CSRF-токена из куки
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    const csrftoken = getCookie('csrftoken');
    console.log('CSRF token:', csrftoken); // для отладки

    function loadStreams() {
        $.get('/api/campaigns/' + campaignId + '/streams/', function(data) {
            renderStreams(data);
        });
    }

    function renderStreams(streams) {
        var $container = $('#streams-container');
        $container.empty();
        streams.forEach(function(stream) {
            var $streamDiv = $('<div class="stream" data-stream-id="' + stream.id + '"></div>');
            if (!stream.offers.every(function(o) { return o.synced; })) {
                $streamDiv.addClass('unsynced');
            }
            $streamDiv.append('<h3>Stream #' + stream.keitaro_id + ' (' + stream.stream_type + ')</h3>');
            if (stream.stream_type === 'offer') {
                var $table = $('<table><tr><th>Offer ID</th><th>Name</th><th>Weight</th><th>Pinned</th><th>Actions</th></tr></table>');
                stream.offers.forEach(function(offer) {
                    var $row = $('<tr class="' + (offer.is_active ? '' : 'removed') + '"></tr>');
                    $row.append('<td>' + offer.offer_id + '</td>');
                    $row.append('<td>' + offer.offer_name + '</td>');
                    $row.append('<td>' + offer.weight + '%</td>');
                    $row.append('<td>' + (offer.pinned ? 'Yes' : 'No') + '</td>');
                    var actions = '';
                    if (offer.is_active) {
                        actions += '<button class="btn-small pin-btn" data-id="' + offer.id + '">' + (offer.pinned ? 'Unpin' : 'Pin') + '</button>';
                        actions += '<button class="btn-small remove-btn" data-id="' + offer.id + '">Remove</button>';
                    } else {
                        actions += '<button class="btn-small restore-btn" data-id="' + offer.id + '">Bring Back</button>';
                    }
                    $row.append('<td>' + actions + '</td>');
                    $table.append($row);
                });
                $streamDiv.append($table);
                // Поле для добавления нового оффера
                var $addDiv = $('<div><input class="offer-search" placeholder="Search offer by name/ID"> <button class="add-offer-btn">Add Offer</button></div>');
                $streamDiv.append($addDiv);
            } else {
                $streamDiv.append('<p>Google redirect stream (no offers)</p>');
            }
            $container.append($streamDiv);
        });

        // Автокомплит для поиска офферов
        $('.offer-search').autocomplete({
            source: '/api/search_offers/',
            minLength: 2,
            select: function(event, ui) {
                $(this).data('selected-id', ui.item.id);
                $(this).val(ui.item.label);
                return false;
            }
        });
    }

    // ----- Обработчики с явной передачей CSRF-токена в заголовке -----

    // Добавление оффера
    $('#streams-container').on('click', '.add-offer-btn', function() {
        var $input = $(this).siblings('.offer-search');
        var offerId = $input.data('selected-id');
        if (!offerId) return;
        var streamId = $(this).closest('.stream').data('stream-id');
        $.ajax({
            url: '/api/streams/' + streamId + '/add_offer/',
            method: 'POST',
            headers: { 'X-CSRFToken': csrftoken },
            contentType: 'application/json',
            data: JSON.stringify({ offer_id: offerId }),
            success: function(data) {
                loadStreams();
            },
            error: function(xhr) {
                alert('Error: ' + xhr.status + ' - ' + (xhr.responseJSON?.error || xhr.responseText || 'Unknown error'));
            }
        });
    });

    // Удаление оффера (мягкое)
    $('#streams-container').on('click', '.remove-btn', function() {
        var id = $(this).data('id');
        $.ajax({
            url: '/api/stream-offers/' + id + '/remove/',
            method: 'POST',
            headers: { 'X-CSRFToken': csrftoken },
            success: function() {
                loadStreams();
            },
            error: function(xhr) {
                alert('Error: ' + xhr.status + ' - ' + (xhr.responseJSON?.error || xhr.responseText));
            }
        });
    });

    // Восстановление оффера
    $('#streams-container').on('click', '.restore-btn', function() {
        var id = $(this).data('id');
        $.ajax({
            url: '/api/stream-offers/' + id + '/restore/',
            method: 'POST',
            headers: { 'X-CSRFToken': csrftoken },
            success: function() {
                loadStreams();
            },
            error: function(xhr) {
                alert('Error: ' + xhr.status + ' - ' + (xhr.responseJSON?.error || xhr.responseText));
            }
        });
    });

    // Pin/Unpin
    $('#streams-container').on('click', '.pin-btn', function() {
        var id = $(this).data('id');
        $.ajax({
            url: '/api/stream-offers/' + id + '/pin/',
            method: 'POST',
            headers: { 'X-CSRFToken': csrftoken },
            success: function() {
                loadStreams();
            },
            error: function(xhr) {
                alert('Error: ' + xhr.status + ' - ' + (xhr.responseJSON?.error || xhr.responseText));
            }
        });
    });

    // Fetch streams
    $('#fetch-btn').click(function() {
        $.ajax({
            url: '/api/campaigns/' + campaignId + '/fetch/',
            method: 'POST',
            headers: { 'X-CSRFToken': csrftoken },
            success: function() {
                loadStreams();
            },
            error: function(xhr) {
                alert('Error: ' + xhr.status + ' - ' + (xhr.responseJSON?.error || xhr.responseText));
            }
        });
    });

    // Push streams
    $('#push-btn').click(function() {
        $.ajax({
            url: '/api/campaigns/' + campaignId + '/push/',
            method: 'POST',
            headers: { 'X-CSRFToken': csrftoken },
            success: function() {
                loadStreams();
            },
            error: function(xhr) {
                alert('Error: ' + xhr.status + ' - ' + (xhr.responseJSON?.error || xhr.responseText));
            }
        });
    });

    // Cancel changes
    $('#cancel-btn').click(function() {
        $.ajax({
            url: '/api/campaigns/' + campaignId + '/cancel/',
            method: 'POST',
            headers: { 'X-CSRFToken': csrftoken },
            success: function() {
                loadStreams();
            },
            error: function(xhr) {
                alert('Error: ' + xhr.status + ' - ' + (xhr.responseJSON?.error || xhr.responseText));
            }
        });
    });

    // Первоначальная загрузка
    loadStreams();
});