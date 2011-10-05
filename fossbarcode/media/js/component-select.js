// used by both the input tab, and the modal line_edit tabs

function select_to_component() {
    var cindex = document.getElementById("id_component_select").value;
    if (cindex == "manual_entry") {
        component_disabled(false);
        for(var f in bom_fields) {
            if (f != "foss_patches") {
                var id = "id_" + f;
                if (f != "foss_license") {
                    document.getElementById(id).value = "";
                } else {
                    var options = document.getElementById(id).children;
                    options.item(0).selected = "selected";
                }
            }
        }
    } else if (cindex == "") {
        return 0;
    } else {
        for(var f in bom_fields) {
            if (f != "foss_version" && f != "foss_spdx" && f != "foss_patches") {
                var id = "id_" + f;
                var src = f.replace("foss_", "");
                if (f != "foss_license") {
                    document.getElementById(id).value = ccache[cindex]['fields'][src];
                } else {
                    var license_id = ccache[cindex]['fields']['license_id'];
                    var options = document.getElementById(id).children;
                    for (i=0; i<options.length; i++) {
                        if (options.item(i).value == license_id) {
                            options.item(i).selected = "selected";
                        } else {
                            options.item(i).selected = "";
                        }
                    }
                }
            }
        }
        component_disabled(true);
        document.getElementById("id_component_select")[0].selected = true;
    }
}
function component_disabled(mode) {
    for(var f in bom_fields) {
        var id = "id_" + f;
        if (f == "foss_license_url") {
            var license_id = document.getElementById("id_foss_license").value;
            if (license_id == -2) {
                document.getElementById(id).disabled = true;
            } else {
                document.getElementById(id).disabled = mode;
            }
        } else if (f == "foss_copyright" || f == "foss_attribution") {
            if (document.getElementById(id).value != '') {
                document.getElementById(id).disabled = mode;
                var select_id = f + "_select";
                document.getElementById(select_id).disabled = mode;
            }
        } else if (f != "foss_version" && f != "foss_spdx" && f != "foss_patches") {
            document.getElementById(id).disabled = mode;
        }
    }
}

