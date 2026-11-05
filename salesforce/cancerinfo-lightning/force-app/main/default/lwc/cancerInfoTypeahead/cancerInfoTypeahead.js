import { LightningElement, api } from 'lwc';
import { filterOptions, MAX_SUGGESTIONS } from 'c/cancerInfoUtils';

/**
 * Accessible SLDS combobox with live, ranked suggestions.
 *
 * Events (none bubble out of the parent's shadow tree):
 *  - textchange   detail: { value }               fired on every keystroke
 *  - optionselect detail: { value, label, option } fired when a suggestion is picked
 *  - submitsearch                                  fired on Enter when no suggestion is highlighted
 */
export default class CancerInfoTypeahead extends LightningElement {
    @api label;
    @api placeholder;
    @api fieldLevelHelp;
    @api iconName = 'utility:search';
    @api optionIcon = 'utility:search';
    @api maxLength = 500;
    @api matchMode = 'all';
    @api noMatchText = 'No matches';
    @api required = false;
    @api disabled = false;
    @api showOnFocus = false;

    _options = [];
    _value = '';
    isOpen = false;
    activeIndex = -1;

    @api
    get options() {
        return this._options;
    }
    set options(value) {
        this._options = Array.isArray(value) ? value : [];
        this.activeIndex = -1;
    }

    @api
    get value() {
        return this._value;
    }
    set value(v) {
        this._value = v || '';
    }

    /** Lets the parent move focus here (e.g. after validation errors). */
    @api
    focus() {
        const input = this.refs.input;
        if (input) {
            input.focus();
        }
    }

    get inputValue() {
        return this._value;
    }

    get matches() {
        return filterOptions(this._options, this._value, this.matchMode, this.showOnFocus, MAX_SUGGESTIONS);
    }

    get results() {
        return this.matches.map((option, index) => {
            const active = index === this.activeIndex;
            return {
                ...option,
                index,
                key: `${option.value}-${index}`,
                icon: option.icon || this.optionIcon,
                active: active ? 'true' : 'false',
                ariaSelected: active ? 'true' : 'false',
                cssClass:
                    'slds-media slds-listbox__option slds-listbox__option_entity slds-listbox__option_has-meta ci-option' +
                    (active ? ' slds-has-focus' : '')
            };
        });
    }

    get hasResults() {
        return this.matches.length > 0;
    }

    get showNoMatch() {
        return this.isOpen && !this.hasResults && this._value.trim().length > 0 && Boolean(this.noMatchText);
    }

    get showDropdown() {
        return this.isOpen && (this.hasResults || this.showNoMatch);
    }

    get comboboxClass() {
        return (
            'slds-combobox slds-dropdown-trigger slds-dropdown-trigger_click' + (this.showDropdown ? ' slds-is-open' : '')
        );
    }

    get ariaExpanded() {
        return this.showDropdown ? 'true' : 'false';
    }

    get showClear() {
        return this._value.length > 0 && !this.disabled;
    }

    renderedCallback() {
        // LWC rewrites element ids at runtime, so aria-activedescendant is wired up after render.
        const input = this.refs.input;
        if (!input) {
            return;
        }
        const active = this.template.querySelector('[data-active="true"]');
        if (active && this.showDropdown) {
            input.setAttribute('aria-activedescendant', active.id);
            if (typeof active.scrollIntoView === 'function') {
                active.scrollIntoView({ block: 'nearest' });
            }
        } else {
            input.removeAttribute('aria-activedescendant');
        }
    }

    handleInput(event) {
        this._value = event.target.value;
        this.isOpen = true;
        this.activeIndex = -1;
        this.dispatchEvent(new CustomEvent('textchange', { detail: { value: this._value } }));
    }

    handleFocus() {
        this.isOpen = true;
    }

    handleBlur() {
        this.isOpen = false;
        this.activeIndex = -1;
    }

    handleKeyDown(event) {
        const count = this.matches.length;
        switch (event.key) {
            case 'ArrowDown':
                event.preventDefault();
                this.isOpen = true;
                if (count) {
                    this.activeIndex = (this.activeIndex + 1) % count;
                }
                break;
            case 'ArrowUp':
                event.preventDefault();
                this.isOpen = true;
                if (count) {
                    this.activeIndex = this.activeIndex <= 0 ? count - 1 : this.activeIndex - 1;
                }
                break;
            case 'Enter':
                event.preventDefault();
                if (this.showDropdown && this.activeIndex >= 0 && this.activeIndex < count) {
                    this.selectOption(this.matches[this.activeIndex]);
                } else {
                    this.isOpen = false;
                    this.dispatchEvent(new CustomEvent('submitsearch'));
                }
                break;
            case 'Escape':
                if (this.isOpen) {
                    event.preventDefault();
                    this.isOpen = false;
                    this.activeIndex = -1;
                }
                break;
            default:
                break;
        }
    }

    preventBlur(event) {
        // Keeps focus in the input so a click on a suggestion registers before blur closes the list.
        event.preventDefault();
    }

    handleOptionClick(event) {
        const index = Number(event.currentTarget.dataset.index);
        const option = this.matches[index];
        if (option) {
            this.selectOption(option);
        }
    }

    handleClear() {
        this._value = '';
        this.activeIndex = -1;
        this.isOpen = this.showOnFocus;
        this.dispatchEvent(new CustomEvent('textchange', { detail: { value: '' } }));
        this.focus();
    }

    selectOption(option) {
        this._value = option.label;
        this.isOpen = false;
        this.activeIndex = -1;
        this.dispatchEvent(
            new CustomEvent('optionselect', {
                detail: { value: option.value, label: option.label, option: { ...option } }
            })
        );
    }
}
