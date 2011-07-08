/*
 * SimpleModal Basic Modal Dialog
 * http://www.ericmmartin.com/projects/simplemodal/
 * http://code.google.com/p/simplemodal/
 *
 * Copyright (c) 2010 Eric Martin - http://ericmmartin.com
 *
 * Licensed under the MIT license:
 *   http://www.opensource.org/licenses/mit-license.php
 *
 * Revision: $Id: basic.js 254 2010-07-23 05:14:44Z emartin24 $
 */

jQuery(function ($) {
	// Load dialog on page load
	//$('#basic-modal-content').modal();

    // history modal loads the history template/view
    $('#history-modal .basic').click(function(e) {
        // see which record we're looking for
        var clicked = $(this).attr("name");
        if (clicked.search("history") != -1 ) {
            var record = clicked.replace("history", "");
            var src = "/barcode/" + record + "/history/";
            $.modal('<iframe src="' + src + '" height="450" width="830" style="border:0">', {
                containerCss:{
                    height:450,
                    padding:0,
                    width:930, 
                    maxWidth: 900
                },
            });
        } else {
            $.modal('<h3>Unable to retrieve history...</h3>');
        }
        return false;
    });

	// for editing the header from the detail page
	$('#header-modal .basic').click(function (e) {
        // see which record we're looking for
        var clicked = $(this).attr("name");
        if (clicked.search("header") != -1 ) {
            var record = clicked.replace("header", "");
            var src = "/barcode/" + record + "/edit_header/";
            $.modal('<iframe src="' + src + '" height="450" width="550" style="border:0">');
        } else {
            $.modal('<h3>Unable to retrieve header...</h3>');
        }
        return false;
	});

    // FIXME - for the input page, we use this - slightly different as we're not hitting the db, just the html
	$('#line-item-modal2 .basic').click(function (e) {
		$('#line-item-modal-content').modal();

		return false;
	});

    // for edits from the detail page, where data is already committed, this one
	$('#line-item-modal .basic').click(function (e) {
       // see which record we're looking for
        var clicked = $(this).attr("name");
        if (clicked.search("line_item") != -1 ) {
            var record = clicked.replace("line_item", "");
            var src = "/barcode/" + record + "/edit_line/";
            $.modal('<iframe src="' + src + '" height="450" width="450" style="border:0">');
        } else {
            $.modal('<h3>Unable to retrieve line_item...</h3>');
        }
        return false;
	});
});
