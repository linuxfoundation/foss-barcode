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
            $.modal('<iframe src="' + src + '" height="450" width="830" style="border:0">');
        } else {
            $.modal('<h3>Unable to retrieve history...</h3>');
        }
        return false;
    });

	// Load dialog on click
	$('#header-modal .basic').click(function (e) {
		$('#header-modal-content').modal();

		return false;
	});
	$('#line-item-modal .basic').click(function (e) {
		$('#line-item-modal-content').modal();

		return false;
	});
});
