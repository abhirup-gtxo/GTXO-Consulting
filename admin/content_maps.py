"""
Content maps: define which HTML elements are editable per page.
Each field: id, label, selector (BS4 CSS), type (text|html|href|attr), attr_name
"""

PAGES = {
    'home': {
        'file': 'index.html',
        'label': 'Home',
        'sections': [
            {
                'label': 'Hero',
                'fields': [
                    {'id': 'hero_eyebrow',   'label': 'Eyebrow Badge',    'selector': '.hero .eyebrow.pill',       'type': 'text'},
                    {'id': 'hero_h1',        'label': 'Headline',         'selector': '.hero h1.display',          'type': 'html',
                     'hint': 'Use <span class="emph">word</span> for italic blue emphasis'},
                    {'id': 'hero_lead',      'label': 'Lead Paragraph',   'selector': '.hero .lead',               'type': 'text'},
                    {'id': 'hero_cta1_text', 'label': 'Primary CTA Text', 'selector': '.hero .btn-cube',           'type': 'text'},
                    {'id': 'hero_cta1_href', 'label': 'Primary CTA Link', 'selector': '.hero .btn-cube',           'type': 'href'},
                    {'id': 'hero_cta2_text', 'label': 'Secondary CTA Text','selector': '.hero .btn-ghost-light',   'type': 'text'},
                    {'id': 'hero_cta2_href', 'label': 'Secondary CTA Link','selector': '.hero .btn-ghost-light',   'type': 'href'},
                ],
            },
            {
                'label': 'Solutions Section',
                'fields': [
                    {'id': 'solutions_eyebrow','label': 'Eyebrow',        'selector': '#solutions .eyebrow',       'type': 'text'},
                    {'id': 'solutions_h2',    'label': 'Heading',         'selector': '#solutions .h2',            'type': 'html'},
                    {'id': 'solutions_lead',  'label': 'Lead Paragraph',  'selector': '#solutions .section-head .lead','type': 'text'},
                ],
            },
            {
                'label': 'Testimonials',
                'fields': [
                    {'id': 'test1_name',  'label': 'Testimonial 1 — Name',  'selector': '.tgrid .t-card:nth-of-type(1) .t-name',  'type': 'text'},
                    {'id': 'test1_role',  'label': 'Testimonial 1 — Role',  'selector': '.tgrid .t-card:nth-of-type(1) .t-role',  'type': 'text'},
                    {'id': 'test1_quote', 'label': 'Testimonial 1 — Quote', 'selector': '.tgrid .t-card:nth-of-type(1) .t-quote', 'type': 'html'},
                    {'id': 'test2_name',  'label': 'Testimonial 2 — Name',  'selector': '.tgrid .t-card:nth-of-type(2) .t-name',  'type': 'text'},
                    {'id': 'test2_role',  'label': 'Testimonial 2 — Role',  'selector': '.tgrid .t-card:nth-of-type(2) .t-role',  'type': 'text'},
                    {'id': 'test2_quote', 'label': 'Testimonial 2 — Quote', 'selector': '.tgrid .t-card:nth-of-type(2) .t-quote', 'type': 'html'},
                    {'id': 'test3_name',  'label': 'Testimonial 3 — Name',  'selector': '.tgrid .t-card:nth-of-type(3) .t-name',  'type': 'text'},
                    {'id': 'test3_role',  'label': 'Testimonial 3 — Role',  'selector': '.tgrid .t-card:nth-of-type(3) .t-role',  'type': 'text'},
                    {'id': 'test3_quote', 'label': 'Testimonial 3 — Quote', 'selector': '.tgrid .t-card:nth-of-type(3) .t-quote', 'type': 'html'},
                ],
            },
        ],
    },

    'about': {
        'file': 'about.html',
        'label': 'About',
        'sections': [
            {
                'label': 'Hero',
                'fields': [
                    {'id': 'hero_h1',    'label': 'Headline',       'selector': '.hero h1.display', 'type': 'html'},
                    {'id': 'hero_lead',  'label': 'Lead Paragraph', 'selector': '.hero .lead',       'type': 'text'},
                    {'id': 'hero_cta1',  'label': 'CTA Text',       'selector': '.hero .btn-cube',   'type': 'text'},
                    {'id': 'hero_cta1_href','label': 'CTA Link',    'selector': '.hero .btn-cube',   'type': 'href'},
                ],
            },
        ],
    },

    'clients': {
        'file': 'clients.html',
        'label': 'Clients',
        'sections': [
            {
                'label': 'Hero',
                'fields': [
                    {'id': 'hero_h1',   'label': 'Headline',       'selector': '.hero h1.display', 'type': 'html'},
                    {'id': 'hero_lead', 'label': 'Lead Paragraph', 'selector': '.hero .lead',       'type': 'text'},
                ],
            },
            {
                'label': 'Stats',
                'fields': [
                    {'id': 'stat1_n', 'label': 'Stat 1 — Number', 'selector': '.stat-row .stat:nth-of-type(1) .n', 'type': 'html'},
                    {'id': 'stat1_l', 'label': 'Stat 1 — Label',  'selector': '.stat-row .stat:nth-of-type(1) .l', 'type': 'text'},
                    {'id': 'stat2_n', 'label': 'Stat 2 — Number', 'selector': '.stat-row .stat:nth-of-type(2) .n', 'type': 'html'},
                    {'id': 'stat2_l', 'label': 'Stat 2 — Label',  'selector': '.stat-row .stat:nth-of-type(2) .l', 'type': 'text'},
                    {'id': 'stat3_n', 'label': 'Stat 3 — Number', 'selector': '.stat-row .stat:nth-of-type(3) .n', 'type': 'html'},
                    {'id': 'stat3_l', 'label': 'Stat 3 — Label',  'selector': '.stat-row .stat:nth-of-type(3) .l', 'type': 'text'},
                ],
            },
            {
                'label': 'Testimonials',
                'fields': [
                    {'id': 'test1_name',  'label': 'Testimonial 1 — Name',  'selector': '.tgrid .t-card:nth-of-type(1) .t-name',  'type': 'text'},
                    {'id': 'test1_role',  'label': 'Testimonial 1 — Role',  'selector': '.tgrid .t-card:nth-of-type(1) .t-role',  'type': 'text'},
                    {'id': 'test1_quote', 'label': 'Testimonial 1 — Quote', 'selector': '.tgrid .t-card:nth-of-type(1) .t-quote', 'type': 'html'},
                    {'id': 'test2_name',  'label': 'Testimonial 2 — Name',  'selector': '.tgrid .t-card:nth-of-type(2) .t-name',  'type': 'text'},
                    {'id': 'test2_role',  'label': 'Testimonial 2 — Role',  'selector': '.tgrid .t-card:nth-of-type(2) .t-role',  'type': 'text'},
                    {'id': 'test2_quote', 'label': 'Testimonial 2 — Quote', 'selector': '.tgrid .t-card:nth-of-type(2) .t-quote', 'type': 'html'},
                    {'id': 'test3_name',  'label': 'Testimonial 3 — Name',  'selector': '.tgrid .t-card:nth-of-type(3) .t-name',  'type': 'text'},
                    {'id': 'test3_role',  'label': 'Testimonial 3 — Role',  'selector': '.tgrid .t-card:nth-of-type(3) .t-role',  'type': 'text'},
                    {'id': 'test3_quote', 'label': 'Testimonial 3 — Quote', 'selector': '.tgrid .t-card:nth-of-type(3) .t-quote', 'type': 'html'},
                ],
            },
        ],
    },

    'contact': {
        'file': 'contact.html',
        'label': 'Contact',
        'sections': [
            {
                'label': 'Hero',
                'fields': [
                    {'id': 'hero_h1',   'label': 'Headline',       'selector': '.hero h1.display', 'type': 'html'},
                    {'id': 'hero_lead', 'label': 'Lead Paragraph', 'selector': '.hero .lead',       'type': 'text'},
                ],
            },
        ],
    },

    'solutions': {
        'file': 'solutions/index.html',
        'label': 'Solutions Hub',
        'sections': [
            {
                'label': 'Hero',
                'fields': [
                    {'id': 'hero_h1',   'label': 'Headline',       'selector': '.hero h1.display', 'type': 'html'},
                    {'id': 'hero_lead', 'label': 'Lead Paragraph', 'selector': '.hero .lead',       'type': 'text'},
                ],
            },
        ],
    },

    'industries': {
        'file': 'industries/index.html',
        'label': 'Industries Hub',
        'sections': [
            {
                'label': 'Hero',
                'fields': [
                    {'id': 'hero_h1',   'label': 'Headline',       'selector': '.hero h1.display', 'type': 'html'},
                    {'id': 'hero_lead', 'label': 'Lead Paragraph', 'selector': '.hero .lead',       'type': 'text'},
                ],
            },
        ],
    },

    'resources': {
        'file': 'resources/index.html',
        'label': 'Resources Hub',
        'sections': [
            {
                'label': 'Hero',
                'fields': [
                    {'id': 'hero_h1',   'label': 'Headline',       'selector': '.hero h1.display', 'type': 'html'},
                    {'id': 'hero_lead', 'label': 'Lead Paragraph', 'selector': '.hero .lead',       'type': 'text'},
                ],
            },
        ],
    },
}
