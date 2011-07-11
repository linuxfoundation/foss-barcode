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

    // header edit doesn't really work as an iframe
	$('#header-modal .basic').click(function (e) {
		$('#header-modal-content').modal({
            containerCss:{
                height:450,
                padding:0,
                width:700
            }
        });
		return false;
	});

    // history popup
	$('#history-modal .basic').click(function (e) {
		$('#history-modal-content').modal({
            containerCss:{
                height:450,
                padding:0,
                width:700
            }
        });
		return false;
	});

    // line edit doesn't work as iframe either
	$('#line-item-modal .basic').click(function (e) {
		$('#line-item-modal-content').modal({
           containerCss:{
                height:450,
                padding:0,
                width:700
            }
        });
		return false;
	});

    // not used, we still need a variant for the input screen though
	$('#line-item-modal2 .basic').click(function (e) {
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
