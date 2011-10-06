// used by both the input tab, and the modal line/header edit tabs

var path_dest = "";
var src_id = "";
// used in several places to differentiate which field we're selecting files for
var pfield = "foss_patches";
var sfield = "foss_spdx";
// filenametoentry needs to update_patch_list in the normal form, not the modal one
var modal = false;

// while the old setup (with reload_filetree code in the .ready) works on the input page
// had issues in the detail/modal edit, so make it callable
$(document).ready( function() {
    reload_filetree();
});
function reload_filetree() {
    $('#target').fileTree({
        root: '/',
        script: '/barcode/dirlist/',
        loadMessage: 'waiting to load'
        }, function(file) {
            filenametoentry(file);
    });
    // header edit modal form needs a different target
    $('#targeth').fileTree({
        root: '/',
        script: '/barcode/dirlist/',
        loadMessage: 'waiting to load'
        }, function(file) {
            filenametoentry(file);
    });
}
function set_destination(dest, source_id) {
    path_dest = dest;
    src_id = source_id;
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
        if (path_dest.search("foss_patches") >= 0) {
            document.getElementsByName(path_dest)[0].value += filename + "\n";
        } else {
            // replace, don't append
            document.getElementsByName(path_dest)[0].value = filename;
            if ([sfield, 'spdx_file'].indexOf(path_dest) >= 0) {
                // trigger onchange so we can enable/disable header/detail spdx stuff
                document.getElementsByName(path_dest)[0].onchange();
            }
            // hide after select for the single file mode
            hide_element(src_id);
        }        
        if ((path_dest.indexOf(pfield) != -1) && (modal != true))
            update_patch_list(path_dest);
    }
}
// 4 functions below all involved in the various ops for the "fake" file inputs
function file_input_to_field(sid, did) {
    document.getElementById(did).value = extractFilename(document.getElementById(sid).value);
}
function extractFilename(path) {  
    var x;
    x = path.lastIndexOf('\\');
    if (x >= 0) // Windows-based path
        return path.substr(x+1);
    x = path.lastIndexOf('/');
    if (x >= 0) // Unix-based path
        return path.substr(x+1);
    return path; // just the filename
}
function clear_value_by_id(did) {
    document.getElementById(did).value = '';
}
function clear_field(fname) {
    document.getElementById(fname).value = '';
}

