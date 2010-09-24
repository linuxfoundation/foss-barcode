# Create your views here.
from django.template import Context, loader
from django.shortcuts import render_to_response, get_object_or_404
from compliance.barcode.models import Barcode_Record, SPDX_Files, FOSS_Components, Patch_Files, RecordForm
from django.http import HttpResponse, HttpResponseRedirect
from django.http import Http404
from django.conf import settings
from django.db.models import Q

from compliance import task

import sys, os, re, urllib, subprocess, time

# used for binding and policy
is_static = '(static)'
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
    spdx = SPDX_Files.objects.filter(brecord = record_id)
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
    if request.method == 'POST': # If the form has been submitted...
        recordlist = request.POST.get('recordlist', '')
        if recordlist != '':
            records = recordlist.split(",")

            # delete all the selected records from the database
            for record in records:
                if record != '':
                    delete_record(record)

    latest_record_list = Barcode_Record.objects.order_by('-record_date')
    return render_to_response('barcode/records.html', {'latest_record_list': latest_record_list, 'tab_records': True})

# input form - this is where the real work happens
def input(request):

    # This is the task to be executed.
    def get_deps_task():
        sys.stdout.write("FIXME" + ".\n")
        sys.stdout.flush()
        # run the back end with given parameters and push the data into the database
        errmsg = None
        lastfile = ''
        parentid = 0
        libparentid = 0
        sys.stdout.write("FIXME...\n")
        sys.stdout.flush()
        proc = subprocess.Popen(cli_command.split(), bufsize=bufsize, stdout=subprocess.PIPE)
        for data in iter(proc.stdout.readline,''):
            errmsg, lastfile, parentid, libparentid = process_results(data, testid, lastfile, parentid, libparentid)
            # if we got an error, delete the test entry
            if errmsg:
                delete_test_record(testid)
                sys.stdout.write("MSGADD: <b>Error: " + errmsg + "</b>\n")
                sys.stdout.flush()   
                time.sleep(30)
                return

            try:
                (rlevel, item) = data.strip().split(",")[:2]
                sys.stdout.write("MSGADD: %s (%s)\n" % (item, rlevel))
            except:
                sys.stdout.write("MSGADD: " + data)
            sys.stdout.flush()

        if not errmsg:
            mark_test_done(testid)
            update_license_bindings()
            sys.stdout.write("MSGADD: Test Id=" + str(testid) + "\n")
            sys.stdout.flush()   
            sys.stdout.write('MSGADD: Test Complete, click <a href="/barcode/' + str(testid) + '/detail/">here</a> to view results\n')
            sys.stdout.flush()
            # FIXME - the redirect doesn't happen without a delay here
            time.sleep(5)
       
    infomsg = None
    tm = task.TaskManager()

    if request.method == 'POST': # If the form has been submitted...
        recordform = RecordForm(request.POST) # A form bound to the POST data
        if recordform.is_valid(): # All validation rules pass
            recorddata = recordform.save(commit=False)       
            recorddata.save()
            recordid = recorddata.id

            # if we have spdx files, store their paths and save them
            if recordform.cleaned_data['spdx_files'] != "":
                spdx_list = recordform.cleaned_data['spdx_files'].split("\n")
                for spdx in spdx_list:
                    if spdx != "":
                        spdxdata = SPDX_Files(brecord_id = recordid, path = spdx)
                        spdxdata.save()
                        # FIXME - copy the files somewhere

            # if we have foss components, store them also, and the patches
            foss_components = request.POST.get('foss_components', '')
            foss_versions = request.POST.get('foss_versions', '')
            if foss_components != '':
                components = foss_components.split(",")
                versions = foss_versions.split(",")
                i = 0
                for foss in components:
                    if foss != "":
                        fossdata = FOSS_Components(brecord_id = recordid, package = foss, version = versions[i])
                        fossdata.save()
                        fossid = fossdata.id
                    # check for patches
                    patch_files = request.POST.get('patch_files' + str(i), '')
                    print patch_files
                    if patch_files != "":
                        patches = patch_files.split("\n")
                        for patch in patches:
                            if patch != "":
                                patchdata = Patch_Files(frecord_id = fossid, path = patch)
                                patchdata.save()
                                # FIXME - copy the files somewhere
                    i = i + 1

            # FIXME - generate the checksum/barcode here

        else:
            print "missing data..."
            print recordform.errors

            #if not tm.is_running():
            #    tm.start(get_deps_task)
            #    return HttpResponseRedirect('/barcode/input/')
            
    else:
        recordform = RecordForm() # An unbound form

    return render_to_response('barcode/input.html', {
                              'recordform': recordform,
                              'tab_input': True,
                              'reload_running': tm.is_running(),
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
        # docs are created yet, try to do it
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

# build up an archive
def record_to_checksum(recid):
    checksum = 0
    # write the record to a temporary file, where the patches and spdx files reside
    # tar the whole thing up
    # tar -cf - . | md5sum -
    # remove the record file
    return checksum

# create eps and png files from a checksum
def checksum_to_barcode(checksum):
    # barcode -b 9128461809d8c5942a20a8167d7101ce -e 128 -m "0,0" -E > 333.ps
    # pstopnm -xsize 500 -portrait -stdout 333.ps | pnmtopng > 333.png
    return 0

# to remove a record
def delete_record(recid):
    q = Barcode_Record.objects.filter(id = recid)
    q.delete()

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
            patches += p.path + "<br>"
        foss.append({'component': f.package, 'version': f.version, 'patches': patches})
    return foss

