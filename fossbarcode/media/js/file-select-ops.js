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
    //reload_filetree();
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
// several functions below all involved in the various ops for the "fake" file inputs
function file_input_to_field(sid, did) {
    var finput = document.getElementById(sid);
    var flist = "";
    if (finput.files.length > 1) {
        for (var x = 0; x < finput.files.length; x++) {
            flist += finput.files[x].name + "\n"
        }
    } else {
        flist = finput.files[0].name
    }
    document.getElementById(did).value = flist;
    encode_file_data(sid, did);
}
function clear_value_by_id(did) {
    document.getElementById(did).value = '';
}
function clear_extra(did, attr) {
    document.getElementById(did).attributes[attr].value = '';
}
function clear_field(fname) {
    document.getElementById(fname).value = '';
}
// Check for the File API support.
function checkForFileAPI() { 
    if (window.File && window.FileReader && window.FileList && window.Blob) {
        // Great success! All the File APIs are supported.
    } else {
        alert('The File APIs are not fully supported in this browser, you will most likely have issues attaching files.');
    }
}
function encode_file_data(sid, did) {   
    var files = document.getElementById(sid).files;
    if (files.length == 0) {
        return;
    }
    // clear before we start
    document.getElementById(did).setAttribute("encoded_data", "");
       
    for (var i = 0, f; f = files[i]; i++) {
        var reader = new FileReader();
        
        reader.onload = (function(theFile) {
            return function(e, flist) {
                // strip off the mime type prefix, less data to send and back end doesn't need it
                var basedata = e.target.result.split(",")[1];
                // grab what's already there for multi
                var olddata = document.getElementById(did).attributes["encoded_data"].value;
                if (olddata != "") {
                    var newdata = olddata + "\n" + basedata;
                    document.getElementById(did).setAttribute("encoded_data", newdata);
                } else {
                    document.getElementById(did).setAttribute("encoded_data", basedata);
                }           
            };
        })(f);

        reader.readAsDataURL(f);
    }
    // and clear when we're done
    clear_value_by_id(sid);
}
