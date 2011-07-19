// used by both the input tab, and the modal line_edit tabs

var path_dest = "";
// used in several places to differentiate which field we're selecting files for
var pfield = "foss_patches";
var sfield = "foss_spdx";
// filenametoentry needs to update_patch_list in the normal form, not the modal one
var modal = false;

$(document).ready( function() {
    $('#target').fileTree({
        root: '/',
        script: '/barcode/dirlist/',
        loadMessage: 'waiting to load'
        }, function(file) {
            filenametoentry(file);
    });
});
function set_destination(dest) {
    path_dest = dest;
}
function toggle_enabled(button) { 
    var e = document.getElementsByName(button)[0];
    if (typeof e != 'undefined') {
        if (e.disabled == true)
            e.disabled = false;
        else
            e.disabled = true;
    }     
}
function filenametoentry(filename) {
    lastchar = filename.slice(-1);
    // only files, no dirs
    if (lastchar != '/') {
        if (path_dest == sfield) {
            // replace, don't append
            document.getElementsByName(path_dest)[0].value = filename;
        } else {
            document.getElementsByName(path_dest)[0].value += filename + "\n";
        }
        if ((path_dest.indexOf(pfield) != -1) && (modal != true))
            update_patch_list(path_dest);
    }
}
