// used by both the input tab, and the modal line/header edit tabs

var path_dest = "";
var src_id = "";
// used in several places to differentiate which field we're selecting files for
var pfield = "foss_patches";
var sfield = "foss_spdx";

// several functions below all involved in the various ops for the "fake" file inputs
function file_input_to_field(sid, did, attach_and_clear) {
    // if attach_and_clear is false, we just copy the name, we'll process the file input on the back end
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
    
    // copy file data to special attribute and clear when we're done if called for
    // we use this for cases like the BoM, where we'll submit multiple files (of the same category) at once
    if (attach_and_clear == true) {
        encode_file_data(sid, did); 
        clear_value_by_id(sid);
    }
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
}
