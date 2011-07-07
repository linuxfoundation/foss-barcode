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

	// Load dialog on click
	$('#history-modal .basic').click(function (e) {
		$('#history-modal-content').modal();

		return false;
	});
	$('#header-modal .basic').click(function (e) {
		$('#header-modal-content').modal();

		return false;
	});
	$('#line-item-modal .basic').click(function (e) {
		$('#line-item-modal-content').modal();

		return false;
	});
});
