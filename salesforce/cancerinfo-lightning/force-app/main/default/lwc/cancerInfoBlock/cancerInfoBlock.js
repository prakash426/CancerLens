import { LightningElement, api } from 'lwc';
import { safeHref } from 'c/cancerInfoUtils';

/**
 * Renders one parsed CancerInfo content block (heading, paragraphs, bullet lists or tiles)
 * followed by its source attribution, as required by the sources' reuse conditions.
 *
 * layout: 'bullets' (default) | 'tiles' (symptom grid) | 'compact' (sidebar cards)
 */
export default class CancerInfoBlock extends LightningElement {
    @api block;
    @api layout = 'bullets';
    @api hideSources = false;

    get isTiles() {
        return this.layout === 'tiles';
    }

    get containerClass() {
        return `ci-block ci-block_${this.layout || 'bullets'}${this.block && this.block.isConsensus ? ' ci-block_consensus' : ''}`;
    }

    get heading() {
        return this.block ? this.block.heading : null;
    }

    get region() {
        return this.block ? this.block.region : null;
    }

    get showRegionInSource() {
        return Boolean(this.region && !this.heading);
    }

    get isConsensus() {
        return Boolean(this.block && this.block.isConsensus);
    }

    get parts() {
        const block = this.block || {};
        return (block.parts || []).map((part, index) => {
            const key = `${block.id}-${part.key || index}`;
            const items = (part.items || []).map((text, i) => ({ key: `${key}-${i}`, text }));
            return {
                key,
                isList: part.isList && !this.isTiles,
                isTiles: part.isList && this.isTiles,
                isText: !part.isList && !part.isSubheading,
                isSubheading: part.isSubheading,
                textClass: part.isIntro ? 'ci-intro' : 'ci-paragraph',
                text: part.text,
                items
            };
        });
    }

    get sources() {
        const block = this.block || {};
        return (block.sources || []).map((s, index) => ({
            key: `${block.id}-src-${index}`,
            organization: s.organization || 'Source',
            title: s.title,
            href: safeHref(s.url),
            updated: s.updated,
            attribution: s.attribution
        }));
    }

    get showSources() {
        return !this.hideSources && this.sources.length > 0;
    }

    get firstSourceHref() {
        const first = this.sources.find((s) => s.href);
        return first ? first.href : null;
    }

    get showReadMore() {
        return Boolean(this.block && this.block.truncated && this.firstSourceHref);
    }
}
