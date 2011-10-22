// used to track queued files
var fupload_total = 0;
var fqueued_total = 0;

// several functions below all involved in the various ops for the "fake" file inputs
function file_input_to_field(sid, did, attach_and_clear) {
    // if attach_and_clear is false, we just copy the name, we'll process the file input on the back end
    var finput = document.getElementById(sid);
    var flist = "";
    if (finput.files.length > 1) {
        for (var x = 0; x < finput.files.length; x++) {
            flist += finput.files[x].name + "\n";
        }
    } else {
        flist = finput.files[0].name;
    }
    document.getElementById(did).value = flist;

    // copy file data to special attribute and clear when we're done if called for
    // we use this for cases like the BoM, where we'll submit multiple files (of the same category) at once
    if (attach_and_clear == true) {
        handle_file_data(sid, did); 
        clear_value_by_id(sid);
    }
}
function clear_value_by_id(did) {
    document.getElementById(did).value = '';
}
function clear_extras(did, attr_list) {
    for (var attr in attr_list)
        clear_extra(did, attr_list[attr]);
}
function clear_extra(did, attr) {
    var e = document.getElementById(did);
    if (attr == "data_sizes") {
        if (e.attributes[attr]) {
            var a = e.attributes[attr].value;
            var sizes = a.split("\n");
            for (var size in sizes) {
                fupload_total -= sizes[size];
                // a zero size means it's queued, decrement the count
                if (sizes[size] == 0 && fqueued_total > 0)
                    fqueued_total -= 1;
            }
        }
    }
    e.setAttribute(attr, "");
}
function set_extras(did, sid, attr_list) {
    for (var attr in attr_list)
        set_extra(did, sid, attr_list[attr]);
}
function set_extra(did, sid, attr) {
    var dest = document.getElementById(did);
    var src = document.getElementById(sid);
    dest.setAttribute(attr, src.attributes[attr].value);
}
function clear_field(fid) {
    document.getElementById(fid).value = '';
}
// Check for the File API support.
function checkForFileAPI() { 
    if (window.File && window.FileReader && window.FileList && window.Blob) {
        // Great success! All the File APIs are supported.
    } else {
        alert('The File APIs are not fully supported in this browser, you will most likely have issues attaching files.');
    }
}
function append_extra(did, attr, newvalue) {
    var olddata = ""; 
    var dest = document.getElementById(did);
    // grab what's already there for multi
    if (dest.attributes[attr])
        olddata = dest.attributes[attr].value;
    if (olddata != "") {
        var newdata = olddata + "\n" + newvalue;
        dest.setAttribute(attr, newdata);
    } else {
        dest.setAttribute(attr, newvalue);
    }           
}
function clear_progress(did) {
    var o = document.getElementById(did);
    for (var i = o.rows.length; i > 0;i--)
        o.deleteRow(i -1);
}
function handle_file_data(sid, did) {   
    var files = document.getElementById(sid).files;
    if (files.length == 0) {
        return;
    }

    // clear before we start
    clear_extra(did, "encoded_data");
    clear_extra(did, "data_sizes");

    // control to disable and subdir to queue to
    var scid = ""   // button to disable until uploads are done
    var subdir = "" // destination subdir by file type
    if (sid == "id_patches_input_file") {
        scid = document.getElementById("submit_item");
    } else if (["id_m_foss_patches", "id_m_foss_spdx", "id_m_foss_copyright", "id_m_foss_attribution", "id_foss_spdx", "id_foss_copyright", "id_foss_attribution"].indexOf(sid) || sid.search("id_foss_patches")) {
        scid = document.getElementById("submit_record");
    }
    if (sid.search("patch") != -1)
        subdir = "patches";
    if (sid.search("spdx") != -1)
        subdir = "spdx_files";
    if (sid.search("copyright") != -1)
        subdir = "copyrights";
    if (sid.search("attribution") != -1)
        subdir = "attributions";
        
    var fsize_max = fqueue_size_high;
    var qcounter = 0;
    for (var i = 0, f; f = files[i]; i++) {
        // if we've already hit the max, queue even smaller files
        if (fupload_total >= fqueue_total_limit)
            fsize_max = fqueue_size_low;
        if (f.size > fsize_max || (f.size + fupload_total) > fqueue_total_limit) {
            // async upload
            append_extra(did, "encoded_data", "queued");
            append_extra(did, "data_sizes", 0);
            fqueued_total += 1;
            qcounter += 1;
            // file, counter, total files, control to disable
            queued_upload(f, qcounter, fqueued_total, scid, subdir);            
        } else {
            // encode/embed the file data as a field attribute, to be processed by the back end        
            var reader = new FileReader();
            reader.onload = (function(theFile) {
                return function(e) {
                    // strip off the mime type prefix, less data to send and back end doesn't need it
                    var basedata = e.target.result.split(",")[1];
                    append_extra(did, "encoded_data", basedata);                   
                };
            })(f);
            reader.readAsDataURL(f);
            fupload_total += f.size;
            append_extra(did, "data_sizes", f.size);
        }        
    }
}
function queued_upload(file, index, ftotal, scid, subdir) {
    var xhr = new XMLHttpRequest();
    // create progress bar - table layout to force things to spread horizontally
    var o = document.getElementById("progress");
    var otr = o.appendChild(document.createElement("tr"));
    var otd = otr.appendChild(document.createElement("td"));
    var progress = otd.appendChild(document.createElement("p"));
    var progresst = otr.appendChild(document.createElement("td"));
    progresst.innerHTML = "Uploading " + file.name + " (" + file.size + " bytes) (" + index + " of " + ftotal + ")";
    o.appendChild(otr);

    // progress bar
	xhr.upload.addEventListener("progress", function(e) {
    	var pc = parseInt(100 - (e.loaded / e.total * 100));
		progress.style.backgroundPosition = pc + "% 0";
	}, false);

	// file received/failed
	xhr.onreadystatechange = function(e) {
		if (xhr.readyState == 4) {
			progress.className = (xhr.status == 200 ? "success" : "failed");
            if (xhr.status == 200)
                scid.disabled = false;
        }
    };

    // actual upload, disable the submit control
    scid.disabled = true;    
    xhr.open("POST", "/barcode/queued_upload/", true);
    xhr.setRequestHeader("Content-Type", "application/octet-stream");
    xhr.setRequestHeader("X_FILENAME", file.name);
    xhr.setRequestHeader("X_SUBDIR", subdir); 
    xhr.send(file);
}

