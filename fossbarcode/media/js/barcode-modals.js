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

    // header edit modal popup
	$('#header-modal .basic').click(function (e) {
        var clicked = $(this).attr("name");
        header_edit_mode(clicked);
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
          var clicked = $(this).attr("name");
          var record = $(this).attr("id");
          if (clicked.search("history") != -1 ) {
            var row = clicked.replace("history", "");
            history_fill(record);       
            $('#history-modal-content').modal({
              containerCss:{
                height:450,
                padding:0,
                width:700
              }
            });
          } else {
            $.modal('<h3>Unable to retrieve line_item...</h3>');
          }
          return false;
	});

    // line edit modal popup
	$('#line-item-modal .basic').click(function (e) {
        var clicked = $(this).attr("name");
        var record = $(this).attr("id");
        if (clicked.search("line_item") != -1 ) {
            var row = clicked.replace("line_item", "");
            // this function is in the detail page, so it can get the dynamic values
            line_edit_fill(row, record);       
		    $('#line-item-modal-content').modal({
                containerCss:{
                    height:520,
                    padding:0,
                    width:850
                }
            });
        } else {
            $.modal('<h3>Unable to retrieve line_item...</h3>');
        }
		return false;
	});

    // line delete modal
    $('#line-delete-modal .basic').click(function (e) {
        var clicked = $(this).attr("name");
        var record = $(this).attr("id");
        if (clicked.search("line_item") != -1 ) {
            var row = clicked.replace("line_item", "");
            var body_html =  '<form id="itemform" method="post" action="" enctype="multipart/form-data">' +
                             '<h3>Delete line item ' + row + '?</h3>' +
                             '<input type="submit" name="submit" id="delete_item" value="Delete Item">' +
                             '<input type="hidden" name="foss_record_id" id="foss_record_id" value="' + record + '">' +
                             '</form>'
            $.modal(body_html, {
                containerCss:{
                    height:100,
                    padding:0,
                    width:200,
                    "text-align": "center",
                }
            });
        } else {
            $.modal('<h3>Unable to retrieve line_item...</h3>');
        }
        return false;
    });
});
