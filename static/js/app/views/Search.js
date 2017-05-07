import Marionette from 'backbone.marionette';
import Radio from 'backbone.radio';
import Noty from 'noty';

import template from '../templates/search.jst';
import FacetCardListView from './FacetCardList';
import HitCollection from '../collections/Hit';
import HitListView from './HitList';

export default Marionette.View.extend({
    template: template,

    regions: {
        hits: '#hits',
        facets: '#facets'
    },

    ui: {
        totalHits: '#total-hits',
        search: '#search',
        emptyText: '#empty-text',
        loader: '#loader'
    },

    events: {
        'enter @ui.search': 'setQuery',
        'keyup @ui.search': 'pressEnter'
    },

    initialize(options) {
        this.viewId = 'searchView';

        const searchChannel = Radio.channel('search');

        this.listenTo(searchChannel, 'update:facets', this.updateFacets);
        searchChannel.reply('get:facets', this.getFacets.bind(this));
        searchChannel.reply('get:params', this.getParams.bind(this));

        // Search parameters (from the URL bar)
        this.params = options.params;
    },

    onRender() {
        this.$el = this.$el.children();
        this.$el.unwrap();
        this.setElement(this.$el);

        // Show all facet cards
        const facetCardListView = new FacetCardListView();
        facetCardListView.collection.fetch({
            success: () => {
                this.showChildView('facets', facetCardListView);
            }
        });

        // Set query input initial value
        if (this.params.hasOwnProperty('query')) {
            this.getUI('search').val(this.params.query);
            if (this.params.query !== '') {
                setTimeout(() => {
                    this.search();
                }, 500);
            }
        }
    },

    onAttach() {
        // Initialize Material Design
        $.material.init();
    },

    pressEnter(e) {
        const $search = this.getUI('search');
        const query = $search.val();

        // Search on Enter
        if (e.keyCode === 13) {
            $search.trigger('enter', query);
        }
    },

    search() {
        const me = this;
        const query = this.getQuery();
        const facets = this.getFacets();
        const $emptyText = this.getUI('emptyText');
        const $loader = this.getUI('loader');

        me.hits = new HitCollection();

        const params = $.extend({
            start: 0,
            hits_per_page: me.hits.hitsPerPage
        }, me.params);

        if (query || facets) {
            $emptyText.hide();
            $loader.show();
            me.hits.fetch({
                data: $.param(params),
                success: () => {
                    $loader.hide();

                    if (me.hits.length > 0) {
                        me.showChildView('hits', new HitListView({
                            collection: me.hits
                        }));
                    } else {
                        me.getRegion('hits').empty();
                        $emptyText.show();
                        new Noty({
                            type: 'warning',
                            text: 'No hits.'
                        }).show();
                    }

                    // Redraw Facet cards
                    me.getRegion('facets').currentView.render();
                },
                error: (hits, response) => {
                    const error = JSON.parse(response.responseText).message;
                    new Noty({
                        type: 'error',
                        text: error
                    }).show();

                    me.getRegion('hits').empty();
                    $loader.hide();
                    $emptyText.show();
                }
            });
        } else {
            me.getRegion('hits').empty();
            this.getUI('totalHits').text('');
            $emptyText.show();

            // Redraw FacetCardList view
            this.getRegion('facets').currentView.render();
        }
    },

    showMore() {
        const $loader = this.getUI('loader');
        const hitCollection = this.hits;
        const page = ++hitCollection.page;
        const hitsPerPage = hitCollection.hitsPerPage;
        const start = page * hitsPerPage;
        const url = hitCollection.url;
        const params = $.extend({
            start: start,
            hits_per_page: hitsPerPage
        }, this.params);

        $loader.show();
        $.getJSON(url, $.param(params))
            .done((hits) => {
                $loader.hide();
                hitCollection.add(hits);
            })
            .fail((response) => {
                $loader.hide();
                const error = JSON.parse(response.responseText).message;
                new Noty({
                    type: 'error',
                    text: error
                }).show();
            });
    },

    setHash() {
        if ($.isEmptyObject(this.params)) {
            location.hash = 'search';
        } else {
            location.hash = 'search?' + $.param(this.params);
        }
    },

    getQuery() {
        return this.params.hasOwnProperty('query') ? this.params.query : '';
    },

    setQuery(e, query) {
        if (query !== '') {
            this.params.query = query;
        } else {
            if (this.params.hasOwnProperty('query')) {  // eslint-disable-line
                delete this.params.query;
            }
        }
        this.setHash();
    },

    getParams() {
        return this.params;
    },

    setParams(params) {
        this.params = params;

        // Update search input value
        if (params.hasOwnProperty('query')) {
            this.getUI('search').val(params.query);
        }
    },

    getFacets() {
        return this.params.hasOwnProperty('facets') ? this.params.facets : '';
    },

    updateFacets(name, value) {
        const facet = name + ':' + value;

        if (this.params.hasOwnProperty('facets')) {
            if (this.params.facets.indexOf(facet) === -1) {
                // Add facet to the params
                this.params.facets += ' ' + facet;
            } else {
                // Remove facet from the params and trim extra spaces
                this.params.facets = this.params.facets.replace(facet, '');
                this.params.facets = this.params.facets.trim();

                // Don't store empty facet param
                if (this.params.facets === '') {
                    delete this.params.facets;
                }
            }
        } else {
            this.params.facets = facet;
        }

        this.setHash();
    },

    updateTotalHits(hitCollection) {
        const $totalHits = this.getUI('totalHits');

        // Update the total number of hits
        if (hitCollection.length > 0) {
            const total = hitCollection.at(0).get('total');
            $totalHits.text('Total: ' + total + ' hits');
        } else {
            $totalHits.text('');
        }
    }
});
