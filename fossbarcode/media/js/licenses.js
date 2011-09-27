// Code for managing license drop-downs and adding licenses.
// Copyright 2011 Linux Foundation.
// Requires jQuery.

var barcode_licenses_url = '/barcode/licenses/';
var barcode_new_license_url = '/barcode/licenses/new';

function populate_licenses(select_element_id) {
    $.getJSON(barcode_licenses_url, function(data) {
	var items = [];
	items.push('<option value="-2" selected="selected">Select License...</option>\n');
	$.each(data, function() {
	    items.push('<option value="'+ this[0] + '">' + this[1] + '</option>\n');
	});
	items.push('<option value="-1">Other License...</option>\n');
	$('#' + select_element_id).html(items.join(''));
    });
}

function select_license(select_element_id, url_element_id, license_id, old_license_id) {
    $.getJSON(barcode_licenses_url, function(data) {
	var items = [];
	items.push('<option value="-2">Select License...</option>\n');
	$.each(data, function() {
            var new_option = '<option value="'+ this[0] + '"';
            if (Number(this[0]) == license_id) {
                new_option = new_option + ' selected="selected"';
            }
	    items.push(new_option + '>' + this[1] + '</option>\n');
	});
	items.push('<option value="-1">Other License...</option>\n');
	$('#' + select_element_id).html(items.join(''));

	// check whether we need to update a non-blank license URL
	var license_url_element = $('#' + url_element_id);
        if (license_url_element.val() == '') {
            get_license_info(license_id, function(data) {
                $('#' + url_element_id).val(data[3]);
            });
        } else if (Number(old_license_id) >= 0) {
	    get_license_info(old_license_id, function(data) {
		if (license_url_element.val() == data[3]) {
		    get_license_info(license_id, function(data) {
			$('#' + url_element_id).val(data[3]);
		    });
		}
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
    } else if (old_license_id >= 0) {
	get_license_info(old_license_id, function(data) {
	    if ($('#' + license_url_id).val() == data[3]) {
		get_license_info(new_license_id, function(data) {
		    $('#' + license_url_id).val(data[3]);
		});
	    }
	});
    }
}