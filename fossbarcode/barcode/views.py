# Create your views here.
from django.template import Context, loader
from django.shortcuts import render_to_response, get_object_or_404
from fossbarcode.barcode.models import Barcode_Record, SPDX_Files, FOSS_Components, Patch_Files, RecordForm
from django.http import HttpResponse, HttpResponseRedirect
from django.http import Http404
from django.conf import settings

from fossbarcode import task

import sys, os, re, urllib, subprocess, time, shutil

# buffer size for Popen, we want unbuffered
bufsize = -1

### each of these views has a corresponding html page in ../templates/barcode

# task status page - intended for calling in javascript
def taskstatus(request):
    tm = task.TaskManager()
    return HttpResponse(tm.read_status())

# record detail page
def detail(request, record_id):
    foss = render_detail(record_id)
    record_list = Barcode_Record.objects.filter(id = record_id)
    record = record_list[0]
    spdx = []
    spdx_list = SPDX_Files.objects.filter(brecord = record_id)
    for s in spdx_list:
        local_path = os.path.basename(s.path)
        spdx.append({'path': s.path, 'local_path': local_path})
    return render_to_response('barcode/detail.html', {'record': record, 'spdx': spdx, 'foss': foss, 'tab_results': True})

# record search page
def search(request):
    error_message = ""
    if request.method == 'POST': # If the form has been submitted...
        searchsum = request.POST.get('searchsum', '')
        record_list = Barcode_Record.objects.filter(checksum = searchsum)
        if record_list.count() == 0:
            error_message = "Record not found..."
        else:
            id = record_list[0].id
            return HttpResponseRedirect('/barcode/' + str(id) + '/detail/')

    return render_to_response('barcode/search.html', {'error_message': error_message})
 
# record list page - this is also a form, for record deletions
def records(request):
    error_message = ''
    if request.method == 'POST': # If the form has been submitted...
        recordlist = request.POST.get('recordlist', '')
        if recordlist != '':
            records = recordlist.split(",")

            # delete all the selected records from the database
            for record in records:
                if record != '':
                    error_message = delete_record(record)

    latest_record_list = Barcode_Record.objects.order_by('-record_date')
    return render_to_response('barcode/records.html', {'latest_record_list': latest_record_list,
                                                       'error_message': error_message, 
                                                       'tab_records': True })

# input form - this is where the real work happens
def input(request):

    error_message = ''
    error_message = check_for_system_apps()
    foss_components = ''
    foss_versions = ''
    foss_licenses = ''
    foss_urls = ''
    foss_patches = ''

    if request.method == 'POST': # If the form has been submitted...
        recordform = RecordForm(request.POST) # A form bound to the POST data
        # we need these whether it's valid or not to repopulate on a bad submit        
        foss_components = request.POST.get('foss_components', '')
        foss_versions = request.POST.get('foss_versions', '')
        foss_licenses = request.POST.get('foss_licenses', '')
        foss_urls = request.POST.get('foss_urls', '')
        # patches are each in their own text area
        if foss_components != '':
            components = foss_components.split(",")
            for i in range(0, len(components)-1):
                foss_patches += request.POST.get('patch_files' + str(i), '') + ","

        # back to "normal" processing
        if recordform.is_valid(): # All validation rules pass
            recorddata = recordform.save(commit=False)       
            recorddata.save()
            recordid = recorddata.id
            data_dest = os.path.join(settings.USERDATA_ROOT,str(recordid))
            spdx_dest = os.path.join(data_dest, "spdx_files")
            patch_dest = os.path.join(data_dest, "patches")
            try:
                os.mkdir(data_dest)
            except:
                error_message = "Failed to create " + data_dest + "<br>"

            # if we have spdx files, store their paths and save them
            if recordform.cleaned_data['spdx_files'] != "":
                spdx_list = recordform.cleaned_data['spdx_files'].split("\n")
                if spdx_list:
                    try:
                        os.mkdir(spdx_dest)
                    except:
                        error_message = "Failed to create " + spdx_dest + "<br>"
                for spdx in spdx_list:
                    if spdx != "":
                        spdx = spdx[:-1]
                        spdxdata = SPDX_Files(brecord_id = recordid, path = spdx)
                        spdxdata.save()
                        try:
                            shutil.copy(spdx, spdx_dest)
                        except:
                            error_message += "Failed to copy " + str(spdx) + "to " + spdx_dest + "<br>"

            # if we have foss components, store them also, and the patches
            if foss_components != '':
                components = foss_components.split(",")
                versions = foss_versions.split(",")
                licenses = foss_licenses.split(",")
                urls = foss_urls.split(",")
                i = 0
                for foss in components:
                    if foss != "":
                        fossdata = FOSS_Components(brecord_id = recordid, 
                                                   package = foss, version = versions[i],
                                                   license = licenses[i], url = urls[i])
                        fossdata.save()
                        fossid = fossdata.id
                    # check for patches
                    patch_files = request.POST.get('patch_files' + str(i), '')
                    if patch_files != "":
                        try:
                            os.mkdir(patch_dest)
                        except:
                            error_message = "Failed to create " + patch_dest + "<br>"

                        patches = patch_files.split("\n")
                        for patch in patches:
                            patch = patch[:-1]
                            if patch != "":
                                patchdata = Patch_Files(frecord_id = fossid, path = patch)
                                patchdata.save()
                                try:
                                    shutil.copy(patch, patch_dest)
                                except:
                                    error_message += "Failed to copy " + str(patch) + "to " + patch_dest + "<br>"
                    i = i + 1

            # generate the checksum/barcode
            checksum = record_to_checksum(recordid)

            if checksum:
                Barcode_Record.objects.filter(id = recordid).update(checksum = checksum)
                result = checksum_to_barcode(recordid, checksum)
                if result:
                    error_message += "Barcode generation failed...<br>"
            else:
                error_message += "Checksum generation failed...<br>"

            return HttpResponseRedirect('/barcode/' + str(recordid) + '/detail/')

    else:
        recordform = RecordForm() # An unbound form

    return render_to_response('barcode/input.html', {
                              'error_message': error_message, 'recordform': recordform,
                              'foss_components': foss_components, 'foss_versions': foss_versions,
                              'foss_licenses': foss_licenses, 'foss_urls': foss_urls,
                              'foss_patches': foss_patches, 'tab_input': True
    })

### these are all basically documentation support

# doc page
def documentation(request):
    from site_settings import gui_name, gui_version

    # Read the standalone docs, and reformat for the gui
    docs = ''
    status = 0

    try:
        f = open(settings.STATIC_DOC_ROOT + "/docs/index.html", 'r')

    except:
        # docs aren't created yet, try to do it
        status = os.system("cd " + settings.STATIC_DOC_ROOT + "/docs && make")
        if status != 0:
            status = os.system("cd " + settings.STATIC_DOC_ROOT + "/docs && ./text-docs-to-html > index.html.addons")
            if status == 0:
                status = os.system("cd " + settings.STATIC_DOC_ROOT + "/docs && cat index.html.base index.html.addons index.html.footer > index.html")
            else:
                docs = "<b>Error, no index.html in compliance/media/docs.</b><br>"
                docs += "If working with a git checkout or tarball, please type 'make' in the top level directory.<br>"
                docs += "</body>"

    # something worked above
    if not docs:
        f = open(settings.STATIC_DOC_ROOT + "/docs/index.html", 'r')
        doc_index = []
        for line in f:
            #replace the div styles for embedded use
            line = line.replace('<div id="lside">', '<div id="lside_e">')
            line = line.replace('<div id="main">', '<div id="main_e">')
            line = line.replace('<img src="', '<img src="/site_media/docs/')
            doc_index.append(line)
        f.close()
    
        # drop the first 11 lines
        docs = ''.join(doc_index[11:])

    return render_to_response('barcode/documentation.html', 
                              {'name': gui_name, 
                               'version': gui_version, 
                               'gui_docs': docs })

# this does not have a corresponding dirlist.html
# this is dynamic filetree content fed to jqueryFileTree for the input.html file/dir selection
# script for jqueryFileTree points to /barcode/dirlist/
def dirlist(request):
    # filter out some directories that aren't useful from "/"
    not_wanted = [ '/proc', '/dev', '/sys', '/initrd' ]
    r=['<ul class="jqueryFileTree" style="display: none;">']
    try:
        d=urllib.unquote(request.POST.get('dir'))
        content = os.listdir(d)
        # slows things a little, but looks more like 'ls'
        for f in sorted(content, key=unicode.lower):
            ff=os.path.join(d,f)
            if ff not in not_wanted and f != 'lost+found':
                if os.path.isdir(ff): 
                    r.append('<li class="directory collapsed"><a href="#" rel="%s/">%s</a></li>' % (ff,f))
                else:
                    e=os.path.splitext(f)[1][1:] # get .ext and remove dot
                    r.append('<li class="file ext_%s"><a href="#" rel="%s">%s</a></li>' % (e,ff,f))
        r.append('</ul>')
    except Exception,e:
        r.append('Could not load directory: %s' % str(e))
    r.append('</ul>')
    return HttpResponse(''.join(r))

### utility functions

# check for the system utilities we need
# FIXME - what if "which" isn't present?
def check_for_system_apps():
    errmsg = ''
    apps_needed = ['find', 'cat', 'md5sum', 'barcode', 'pstopnm', 'pnmtopng']
    for app in apps_needed:
        result = os.system("which " + app + "> /dev/null")
        if result:
            errmsg += "Could not find system app '<i>" + app + "</i>'...<br>"
            if app == "barcode":
                errmsg += "(See the documentation for building '<i>" + app + "</i>' from source)<br>"

    if errmsg:
        errmsg += "Application will fail to generate barcodes without these apps<br>"
        errmsg += "Please use your system package manager to install them<br>"

    return errmsg

# strip 'pk' entry from serialized data
def strip_pk(data):
    data = re.sub('pk=".*?" ','', data)
    return data

# build up an archive
def record_to_checksum(recid):
    # create an xml file of the database data
    # FIXME - this could be cleaned up a bit, just QandD for now
    # FIXME - record has "pk" in it, so the same user date gets a different checksum
    from django.core import serializers
    data = strip_pk(serializers.serialize("xml", Barcode_Record.objects.filter(id = recid), 
                                  fields=('company','website', 'product', 'version', 'release', 'checksum')))
    has_spdx = SPDX_Files.objects.filter(brecord = recid).count()
    print has_spdx
    if has_spdx:
        data += strip_pk(serializers.serialize("xml", SPDX_Files.objects.filter(brecord = recid), fields=('path')))
    has_foss = FOSS_Components.objects.filter(brecord = recid).count()
    if has_foss:
        data += strip_pk(serializers.serialize("xml", FOSS_Components.objects.filter(brecord = recid), 
                                               fields=('package', 'version')))
        foss_list = FOSS_Components.objects.filter(brecord = recid)
        for f in foss_list:
            fossid = f.id
            has_patches = Patch_Files.objects.filter(frecord = fossid).count()
            if has_patches:
                data += strip_pk(serializers.serialize("xml", Patch_Files.objects.filter(frecord = fossid), 
                                                       fields=('path')))
    
    # write the xml to a temporary file
    working_dir = os.path.join(settings.USERDATA_ROOT, str(recid))
    if os.path.exists(settings.USERDATA_ROOT) == 0:
        try:
            os.mkdir(settings.USERDATA_ROOT)
        except:
            error_message = "Failed to create " + settings.USERDATA_ROOT + "<br>"
    
    if os.path.exists(working_dir) == 0:
        try:
            os.mkdir(working_dir)
        except:
            error_message = "Failed to create " + working_dir + "<br>"

    outf = os.path.join(working_dir, "barcode_data.xml")
    outh = open(outf, "w")
    outh.write(data)
    outh.close

    # tar the whole thing up - no workie - not repeatable
    #checksum = os.popen("tar -C " + working_dir + " -cf - . | md5sum -").readline()
    # cat everything into md5sum
    checksum = os.popen("find " + working_dir + " -type f -exec cat {} + | md5sum -").readline()
 
    # just the number, not the filename
    checksum = checksum[:32]
    # remove the record file
    os.unlink(outf)

    # and return  
    return checksum

# create eps and png files from a checksum
def checksum_to_barcode(recid, checksum):
    # FIXME - can any user write the file to here?
    ps_file = os.path.join(settings.USERDATA_ROOT, str(recid), checksum + ".ps")
    png_file = os.path.join(settings.USERDATA_ROOT, str(recid), checksum + ".png")

    result = os.system("barcode -b " + checksum + " -e 128 -m '0,0' -E > " + ps_file)
    if result == 0:
        result = os.system("pstopnm -xsize 500 -portrait -stdout " + ps_file + " | pnmtopng > " + png_file)
        
    return result

# to remove a record
def delete_record(recid):
    errmsg = ''
    q = Barcode_Record.objects.filter(id = recid)
    checksum = q[0].checksum
    q.delete()
    try:
        shutil.rmtree(os.path.join(settings.USERDATA_ROOT,str(recid)))
    except:
        errmsg += "Failed to delete user data...<br>"
    return errmsg

# delete table records requested by id from one of the input forms
def delete_records(table, rlist):
            
    records = rlist.split(",")

    for record in records:
        if record != '':
            q = table.objects.filter(id = record)
            q.delete()

# pre-render some of the record detail
def render_detail(id):
    foss = []
    foss_list = FOSS_Components.objects.filter(brecord = id)
    for f in foss_list:
        fossid = f.id
        patch_list = Patch_Files.objects.filter(frecord = fossid)
        patches = ""
        for p in patch_list:
            patches += '<a href="/site_media/user_data/' + str(id) + "/patches/" + os.path.basename(p.path) + '">' + p.path + "</a><br>"
        foss.append({'component': f.package, 'version': f.version, 'license': f.license, 'url': f.url, 'patches': patches})
    return foss

