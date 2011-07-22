/*
 * History fill function for record and detail views.
 * Copyright 2011 Linux Foundation.
 */

var history_base_url = "/barcode/RECID/json/history/";
var record_base_url = "/barcode/RECID/detail/";

function history_fill(record) {
    $('#history-modal-content-id').text(record);
    var history_url = history_base_url.replace("RECID", record);
    var record_url = record_base_url.replace("RECID", record);
    $.getJSON(history_url, function(data) {
	var items = [];

	$.each(data, function(index) {
	    items.push('<li><a href="' + record_url + 
		       "?revision=" + $(this)[0] + '">' + 
		       $(this)[1] + '</a>: ' + $(this)[2] + "</li>");
	});

	$('#history-modal-content-list').html('<ul>' + items.join('') + "</ul>");
    });
}
