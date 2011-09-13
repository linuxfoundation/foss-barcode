// Code for managing license drop-downs and adding licenses.
// Copyright 2011 Linux Foundation.
// Requires jQuery.

var barcode_licenses_url = '/barcode/licenses/';
var barcode_new_license_url = '/barcode/licenses/new';

function populate_licenses(select_element_id) {
    $.getJSON(barcode_licenses_url, function(data) {
	var items = [];
	$.each(data, function() {
	    items.push('<option value="'+ this[0] + '">' + this[1] + '</option>\n');
	});
	$('#' + select_element_id).html(items.join(''));
    });
}

function select_license(select_element_id, license_id) {
}

function create_new_license(license_name, license_version, callback) {
    return $.getJSON(barcode_new_license_url,
		     { 'license_name': license_name,
		       'license_version': license_version },
		     callback);
}
