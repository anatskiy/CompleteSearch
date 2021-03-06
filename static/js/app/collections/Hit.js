import Backbone from 'backbone';
import HitModel from '../models/Hit';

export default Backbone.Collection.extend({
    url: 'search/',
    model: HitModel,
    hitsPerPage: 20,
    page: 0
});
