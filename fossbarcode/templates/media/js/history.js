/*
 * History fill function for record and detail views.
 * Copyright 2011 Linux Foundation.
 */

var history_base_url = "{% url history-url idtag %}";
var record_base_url = "{% url detail-url idtag %}";

function history_fill(record) {
    $('#history-modal-content-id').text(record);
    var history_url = history_base_url.replace("{{ idtag }}", record);
    var record_url = record_base_url.replace("{{ idtag }}", record);
    $.getJSON(history_url, function(data) {
	var items = [];

	$.each(data, function(index) {
	    if (index == 0) {
		items.push('<li><a href="' + record_url + '">' + 
			   $(this)[1] + '</a>: ' + $(this)[2] + "</li>");
	    } else {
		items.push('<li><a href="' + record_url + $(this)[0] + '">' + 
			   $(this)[1] + '</a>: ' + $(this)[2] + "</li>");
	    }
	});

	$('#history-modal-content-list').html('<ul>' + items.join('') + "</ul>");
    });
}
