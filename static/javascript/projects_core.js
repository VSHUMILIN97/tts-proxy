let projects = [];

function transferUserTo (path) {
    window.location.href = path
}

new Vue({
    el: '#describe-text'
});

new Vue({
   el: '#add-modal',
    delimiters: ['[[', ']]'],

    data() {
      return {
        form: {
            name: '',
            slug: '',
        },
          errors: {
              common: null,
              common_sh: false,
              name: null,
              name_sh: false,
              slug: null,
              slug_sh: false
          }
      }
    },
    computed: {
        nameState () {
            return this.isValidName()
        }
    },
    methods: {
      handleSubmit() {
          if (!this.isValidName()) {
              return
          }
        console.log(JSON.stringify(this.form));
        axios({
            method: 'post',
            url: projectsCreatePath,
            data: this.form
        })
            .then((response) => {
                console.log(response.data);
                projects.unshift(response.data);
                this.$refs['add-p-mod'].hide();
            }, (error) => {
                console.log(error);
                if (error.response.status >= 500) {
                    this.errors.common = "Internal server error. Try again later";
                    this.errors.common_sh = true;
                }
                console.log(JSON.stringify(error));
                console.log(error.response.data);
                if (!error.response.data) {
                    return
                }
                let data = error.response.data;
                if (data.name) {
                    this.errors.name = data.name;
                    this.errors.name_sh = true;
                }
                if (data.slug) {
                    this.errors.slug = data.slug;
                    this.errors.slug_sh = true;
                }
            });
      },
        handleOk(bvModalEvt) {
        // Prevent modal from closing
        bvModalEvt.preventDefault();
        // Trigger submit handler
        this.handleSubmit();
      },
        isValidName() {
            return this.form.name.length > 2
        },
    }
});

new Vue({

    el: '#projects-dt',
    delimiters: ['[[', ']]'],

    data() {

        return {
            isNotReady: true,

            fields: [
                {'key': 'settings', 'label': ''},
                {'key': 'name', 'label': 'Project name', 'sortable': true},
                {'key': 'slug', 'label': 'Project URI', 'sortable': true},
                {'key': 'last_updated', 'label': 'Last updated', 'sortable': true},
                {'key': 'delete', 'label': 'Delete project'},
            ],
            striped: true,
            projects: null,
            perPage: 15,
            currentPage: 1,
            rows: 0,
        }

    },
    mounted() {
        axios
            .get(projectsListPath)
            .then(response => {
                projects = response.data;
                this.rows = projects.length;
                this.projects = projects;
                this.preventLoading();
            })
            .catch(error => console.log(error))
    },
    methods: {
        inspectProject(row){
            transferUserTo(
                currPage + row.audiorecords
            );
        },
        preventLoading() {
            this.isNotReady = !this.isNotReady;
        },
        confirmDelete(item, index) {
        this.$bvModal.msgBoxConfirm(
            'Please confirm that you want to delete everything.',
            {
                title: 'Please Confirm',
                size: 'sm',
                buttonSize: 'sm',
                okVariant: 'danger',
                okTitle: 'YES',
                cancelTitle: 'NO',
                footerClass: 'p-2',
                hideHeaderClose: false,
                centered: true
            })
          .then(value => {
            if (value === true) {
                axios({
                    method: 'delete',
                    url: projectsDestroyPath + item.slug,
                });
                projects.splice(index, 1)
            }
          })
          .catch(err => {
            // An error occurred
          })
      }

    }

});
