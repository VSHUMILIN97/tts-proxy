let audioRecordArray = [];
let sources = [];
let variants = [];
let sourcesDict = {};

let blockingFocus = false;


window.onbeforeunload = function() {
    if (blockingFocus === false) {
        return
    }
    return "Task in progress!";
};

let makeSourceMap = function(dullSources){
    let mapping = {};
    for (let source in dullSources){
        const name = dullSources[source].name;
        delete dullSources[source].name;
        mapping[name] = dullSources[source];
    }
    return mapping
};


toaster = function(
    that,
    body,
    title,
    hide = null,
    append = true,
    variant='info',
    solid = true,
){
  //  Vue.JS valid function
    let params = {
        title: title,
        variant: variant,
        solid: solid,
        appendToast: append
    };
    if (hide !== null) {
        params['autoHideDelay'] = hide;
    }
    that.$bvToast.toast(body, params);
};


alertTaskInProgress = function(that){
    // Vue.js valid function
    that.$bvToast.toast(
        'Generating content. Do not reload the page', {
            title: 'Task executed at ' + getDateTime(),
            variant: 'info',
            solid: true,
        });
};

getDateTime = function() {
    let today = new Date();
    let date = today.getFullYear()+'-'+(today.getMonth()+1)+'-'+today.getDate();
    let time = today.getHours() + ":" + today.getMinutes() + ":" + today.getSeconds();
    return date+' '+time;
};

// Resources fetch
let reqSources = new XMLHttpRequest();
reqSources.open('GET', sourcesURI, false);
reqSources.send(null);
if (reqSources.status === 200) {
    sources = makeSourceMap(JSON.parse(reqSources.responseText));
    for (let source in sources) {
        sourcesDict[source] = sources[source];
        variants.push({
            "text": source,
            "value": source
        });
    }
bodyContainer.removeClass('blur');
}


addShowDetailsFlag = function(item, index) {
    item['_showDetails'] = false;
};


// Modal form for edit
let editForm = new Vue({
   el: '#edit-audio-record',
    delimiters: ['[[', ']]'],

    data() {
      return {
          tts: '',
          recordId: '',
          voice: '',
          emotion: '',
          url: editAudioURI,
          name: '',
          example: null,
          text: '',
          speed: '1.0',
          ttsSources: [],
          voicesList: [],
          emotionList: [],
          busyState: false,
          form: {
              tts: ''
          },
          errors: {
              common: null,
              common_sh: false,
              style: 'danger'
          }
      }
    },
    computed: {
        textState () {
            return this.isValidText()
        },
    },
    methods: {
       changeTTSSource() {
            if (sourcesDict[this.tts] === undefined){
                return
            }
            this.voicesList = sourcesDict[this.tts].voices;
            this.voice = sourcesDict[this.tts].voices[0];
            if (sourcesDict[this.tts].emote !== null) {
                this.emotionList = sourcesDict[this.tts].emote;
                this.emotion = sourcesDict[this.tts].emote[0];
            } else {
                this.emotion = null;
                this.emotionList = [];
            }
        },
      handleSubmit() {
          if (!this.isValidText()) {
              return
          }
          this.form.tts = sourcesDict[this.tts].id;
          if (this.text !== this.example.text){
              this.form['text'] = this.text;
          }
          if (this.emotion !== this.example.emote) {
              this.form['emotion'] = this.emotion;
          }
          if (this.voice !== this.example.voice){
              this.form['voice'] = this.voice;
          }
          if (this.speed != this.example.playing_speed){
              this.form['speed'] = this.speed;
          }
          const replaceIndex = audioRecordArray.findIndex(
              x => x.name === this.name
          );
          if (Object.keys(this.form).length === 1){
              this.errors.common = 'You have to make changes before update';
              this.errors.common_sh = true;
              this.errors.style = 'warning';
              return;
          }
          this.busyState = true;
          console.log(JSON.stringify(this.form));
          alertTaskInProgress(this);
        axios({
            method: 'post',
            url: this.url + this.recordId,
            data: this.form
        })
            .then((response) => {
                let data = response.data;
                addShowDetailsFlag(data, 0);
                console.log(data);
                audioRecordArray.splice(replaceIndex, 1, data);
                this.audioRecordArray = audioRecordArray;
                this.$refs['edit-am-mod'].hide();
                this.busyState = false;
                blockingFocus = false;
            }, (error) => {
                blockingFocus = false;
                this.busyState = false;
                if (error.response.status === 304) {
                    this.errors.common = 'You have to make changes before update';
                    this.errors.common_sh = true;
                    this.errors.style = 'warning';
                    return;
                }
                if (error.response.status === 404){
                    this.errors.common_sh = true;
                    this.errors.common = 'Requested audio was deleted. Reload page';
                    this.errors.style = 'warning';
                    return;
                }
                if (error.response.status >= 500) {
                    this.errors.common = "Internal server error. Try again later";
                    this.errors.common_sh = true;
                    this.errors.style = 'danger';

                }
                console.log(error.response);
                if (!error.response.data) {

                } else if (this.errors.common === null) {
                    this.errors.common = JSON.stringify(error.response.data);
                    this.errors.common_sh = true;
                }

            });
      },
        handleOk(bvModalEvt) {
            // Prevent modal from closing
            bvModalEvt.preventDefault();
            // Trigger submit handler
            if (sourcesDict[this.tts] === undefined) {
                return
            }
            this.handleSubmit();
      },
        isValidText() {
            return this.text.trim().length >= 1
        },
    }
});


// Data table for audiorecords
new Vue({

    el: '#audios-dt',
    delimiters: ['[[', ']]'],

    data() {

        return {
            isNotReady: true,
            fields: [
                {'key': 'name', 'label': 'Record ID', 'sortable': true},
                {'key': 'text', 'label': 'Text', 'sortable': true},
                {'key': 'modified_at', 'label': 'Last updated', 'sortable': true},
                {'key': 'audio', 'label': 'Sound'},
                {'key': 'source', 'label': 'Source', 'sortable': true},
                {'key': 'voice', 'label': 'Voice', 'sortable': true},
                {'key': 'speed', 'label': 'Record speed'},
                {'key': 'emote', 'label': 'Emotion'},
                {'key': 'settings', 'label': ''}
            ],
            striped: true,
            audioRecordArray: null,
            perPage: 25,
            currentPage: 1,
            rows: null,
        }

    },
    mounted() {
        axios
            .get(audioRecordListPath)
            .then(response => {
                audioRecordArray = response.data;
                audioRecordArray.forEach(addShowDetailsFlag);
                this.rows = audioRecordArray.length;
                this.audioRecordArray = audioRecordArray;
                this.preventLoading();
            })
            .catch(error => console.log(error));
    },
    methods: {
        preventLoading() {
            this.isNotReady = !this.isNotReady;
        },
        showDetails(row) {
            row._showDetails = !row._showDetails;
        },
        openEditModal(row){
            editForm.ttsSources = variants;
            editForm.voicesList = sourcesDict[row.item.source].voices;
            editForm.emotionList = (
                sourcesDict[row.item.source].emote ?
                    sourcesDict[row.item.source].emote : []
            );
            editForm.tts = row.item.source;
            editForm.emotion = row.item.emote;
            let voiceIndex = editForm.voicesList.findIndex(
                x => x.startsWith(row.item.voice)
            );
            editForm.voice = editForm.voicesList[voiceIndex];
            editForm.speed = row.item.playing_speed;
            editForm.name = row.item.name;
            editForm.text = row.item.text;
            editForm.recordId = row.item.id;
            editForm.example = row.item;
            editForm.$refs['edit-am-mod'].show();
        },
        confirmDelete(item, index) {
        this.$bvModal.msgBoxConfirm(
            'Please confirm that you want to delete ' + '"' + item.name + '"',
            {
                title: 'Delete audio record',
                size: 'sm',
                buttonSize: 'sm',
                okVariant: 'danger',
                okTitle: 'Delete',
                cancelTitle: 'Cancel',
                footerClass: 'p-2',
                hideHeaderClose: false,
                centered: true
            })
          .then(value => {
            if (value === true) {
                axios({
                    method: 'delete',
                    url: audioDestroyURI + item.id,
                });
                audioRecordArray.splice(index, 1);
                this.audioRecordArray = audioRecordArray;
            }
          })
          .catch(err => {
            // An error occurred
          })
      }
    }

});


// Modal form for creating audio records
new Vue({
   el: '#audio-modal',
    delimiters: ['[[', ']]'],

    data() {
      return {
          tts: '',
          voice: '',
          emotion: '',
          file: null,
          importOwn: [],
          importVoice: '',
          importOwnReport: false,
          importOwnReportText: '',
          busyStateOwnImport: false,
          speed: '1.0',
          ttsSources: null,
          voicesList: null,
          emotionList: [],
          busyState: false,
          busyStateFile: false,
          form: {
              name: '',
              text: '',
              speed: '',
              tts: '',  // Filled in later
              voice: '',  // Filled in later
              emotion: null,  // May be empty
          },
          errors: {
              name: null,
              name_sh: false,
              text: null,
              text_sh: false,
          }
      }
    },
    mounted() {
       this.tts = Object.keys(sources)[1];
       this.ttsSources = variants;
    },
    computed: {
        nameState () {
            return this.isValidName()
        },
        textState () {
            return this.isValidText()
        },
        changeTTSSource() {
            if (sourcesDict[this.tts] === undefined){
                return
            }
            this.voicesList = sourcesDict[this.tts].voices;
            this.voice = sourcesDict[this.tts].voices[0];
            if (sourcesDict[this.tts].emote !== null) {
                this.emotionList = sourcesDict[this.tts].emote;
                this.emotion = sourcesDict[this.tts].emote[0];
            } else {
                this.emotion = null;
                this.emotionList = [];
            }
        },
    },
    methods: {
      handleSubmit(url) {
          if (!this.isValidName() && !this.isValidText()) {
              return
          }
          this.busyState = true;
          this.form.emotion = this.emotion;
          this.form.voice = this.voice;
          this.form.tts = sourcesDict[this.tts].id;
          this.form.speed = parseFloat(this.speed);
          blockingFocus = true;
          alertTaskInProgress(this);
        axios({
            method: 'post',
            url: url,
            data: this.form
        })
            .then((response) => {
                let data = response.data;
                addShowDetailsFlag(data, 0);
                audioRecordArray.unshift(data);
                this.$refs['add-am-mod'].hide();
                this.form.text = '';
                this.form.name = '';
                this.busyState = false;
                blockingFocus = false;
            }, (error) => {
                this.busyState = false;
                blockingFocus = false;
                if (error.response.status >= 500) {
                    toaster(
                        this,
                        'Internal server error. Try again later',
                        'Audio generation error at ' + getDateTime(),
                        10000,
                        false,
                        'danger',
                    );
                }
                console.log(error.response);
                if (!error.response.data) {
                    return
                }
                let data = error.response.data;
                if (data.name) {
                    this.errors.name = data.name;
                    this.errors.name_sh = true;
                }
                toaster(
                    this,
                    JSON.parse(data),
                    'Audio generation error at ' + getDateTime(),
                    10000,
                    false,
                    'danger',
                );
            });
      },
        // File import (CSV/IMED/XLS)
        handleFileSubmit() {
          this.busyState = true;
          let formData = new FormData();
          formData.append('export-file', this.file);
          formData.set('emotion', this.emotion);
          formData.set('voice', this.voice);
          formData.set('source', sourcesDict[this.tts].id);
          formData.set('speed', parseFloat(this.speed));
          blockingFocus = true;
          alertTaskInProgress(this);
          axios({
            method: 'post',
            url: fileImportURI,
            data: formData
          })
            .then((response) => {
                console.log(response.data);
                blockingFocus = false;
                location.reload(true);
            }, (error) => {
                this.file = null;
                blockingFocus = false;
                this.busyState = false;
                if (error.response.status >= 500) {
                    toaster(
                        this,
                        'Internal server error. Try again later',
                        'File import error at ' + getDateTime(),
                        10000,
                        false,
                        'danger',
                    );
                }
                if (!error.response.data) {
                    return
                }
                let data = JSON.parse(error.response.data);
                console.log(data);
                if (data.file) {
                    toaster(
                        this,
                        data.file,
                        'File import error at ' + getDateTime(),
                        10000,
                        false,
                        'danger',
                    )
                }
            });
        },
        handleOk(bvModalEvt, update = false) {
            // Prevent modal from closing
            bvModalEvt.preventDefault();
            // Trigger submit handler
            if (sourcesDict[this.tts] === undefined) {
                return
            }
            let url = '';
            if (sourcesDict[this.tts].id == 1) {url = yaURI;} else {url = crtURI;}
            if (update){url = updateAudioURI}
            this.handleSubmit(url);
        },
        handleFileOK(bvModalEvt) {
            bvModalEvt.preventDefault();
            this.handleFileSubmit();
        },
        isValidName() {
            return (
                this.form.name.trim().length >= 1
                && !this.form.name.includes('/')
                && !this.form.name.includes(' ')
            )
        },
        isValidText() {
            return this.form.text.trim().length >= 1
        },
        submitToServer(bvModalEvt) {
            bvModalEvt.preventDefault();
            console.log(this.importOwn);
            this.importOwnReport = false;
            if (this.importVoice.length < 1 ) {
                console.log('Fill in the "voice" field');
                toaster(
                    this,
                    'Fill in "Actor voice" field',
                    'Wrong settings',
                    3000,
                    true,
                    'warning'
                );
                return
            }
            if (this.importOwn.length === 0){
                console.log('Choose more files!');
                return
            }
            this.busyStateOwnImport = true;
            const formData = new FormData();
            formData.append('voice', this.importVoice);
            for (let index = 0; index < this.importOwn.length; index++){
                let file = this.importOwn[index];
                formData.append(file.name, file)
            }
            this.importOwnReportText = '';
            blockingFocus = true;
            this.busyState = true;
            alertTaskInProgress(this);
            axios({
                method: 'POST',
                url: importOwnURI,
                data: formData
            })
                .then((response) => {
                    this.importOwn = [];
                    let data = response.data;
                    console.log(data);
                    blockingFocus = false;
                    this.busyState = false;
                    if (data.errors.length === 0) {
                        toaster(
                            this,
                            (
                                'Import was successful at '
                                + getDateTime()
                                + '. Page will be reloaded within 5 seconds'
                            ),
                            'Successful import',
                            4500,
                            true,
                            'success',
                            true
                        );
                        this.busyStateOwnImport = false;
                        this.$refs.importOwn.hide();
                        setTimeout(function () {
                            location = ''
                        }, 5000);
                    }
                    if (data.errors.length > 0 && data.success.length > 0) {
                        this.busyStateOwnImport = false;
                        toaster(
                            this,
                            'Import was partially successful',
                            'Partial import',
                            5000,
                            true,
                            'warning',
                            true
                        );
                        this.importOwnReport = true;
                        this.importOwnReportText += 'Following files were not imported:\n';
                        for (let index = 0; index < data.errors.length; index++){
                            this.importOwnReportText += (
                                index.toString()
                                + ': '
                                + data.errors[index]
                                + '\n'
                            )
                        }
                        this.importOwnReportText += (
                            'Tip: Reload page to check which files were replaced'
                        )
                    }
                    if (data.success.length === 0) {
                        this.busyStateOwnImport = false;
                        toaster(
                            this,
                            'All uploaded files can\'t be imported',
                            'Import error at ' + getDateTime(),
                            10000,
                            true,
                            'danger',
                            true
                        );
                        this.importOwnReport = true;
                        this.importOwnReportText += 'Following files were not imported:\n';
                        for (let index = 0; index < data.errors.length; index++){
                            this.importOwnReportText += (
                                index.toString()
                                + ': '
                                + data.errors[index]
                                + '\n'
                            )
                        }
                        this.importOwnReportText += (
                            'Tip: Reload page to check which files were replaced'
                        )
                    }
                }, (error) => {
                    console.log(error);
                    blockingFocus = false;
                    this.busyState = false;
                })
        },
    }
});
