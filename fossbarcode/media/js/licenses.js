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
	items.push('<option value="-1">Other License...</option>\n');
	$('#' + select_element_id).html(items.join(''));
    });
}

function select_license(select_element_id, url_element_id, license_id) {
    $.getJSON(barcode_licenses_url, function(data) {
	var items = [];
	$.each(data, function() {
            var new_option = '<option value="'+ this[0] + '"';
            if (Number(this[0]) == license_id) {
                new_option = new_option + ' selected="selected"';
            }
	    items.push(new_option + '>' + this[1] + '</option>\n');
	});
	items.push('<option value="-1">Other License...</option>\n');
	$('#' + select_element_id).html(items.join(''));
        if ($('#' + url_element_id).val() == '') {
            get_license_info(license_id, function(data) {
                $('#' + url_element_id).val(data[3]);
            });
        }
    });
}

function create_new_license(license_name, license_version, license_url, callback) {
    return $.getJSON(barcode_new_license_url,
		     { 'license_name': license_name,
		       'license_version': license_version,
                       'license_url': license_url },
		     callback);
}

function get_license_info(license_id, callback) {
    return $.getJSON(barcode_licenses_url + license_id + "/json/",
		     callback);
}

function update_license_url(new_license_id, old_license_id, license_url_id) {
    if ($('#' + license_url_id).val() == '') {
        get_license_info(new_license_id, function(data) {
            $('#' + license_url_id).val(data[3]);
        });
    }
}