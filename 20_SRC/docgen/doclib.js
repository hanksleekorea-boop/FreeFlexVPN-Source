const d = require('docx');
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, BorderStyle,
  Table, TableRow, TableCell, WidthType, ShadingType, TableOfContents, PageBreak,
  Header, Footer, PageNumber, LevelFormat, convertInchesToTwip
} = d;

const FONT = 'Noto Sans CJK KR';
const C = { ink: '111111', mid: '444444', mute: '777777', line: 'D9D6CF',
            blue: '1F4E9C', green: '11704F', amber: '8A5A00', red: 'A32F2F',
            head: 'EDEBE5', zebra: 'F7F6F2' };

const P = (text, o = {}) => new Paragraph({
  alignment: o.align, spacing: { before: o.before ?? 0, after: o.after ?? 100, line: 300 },
  indent: o.indent,
  border: o.rule ? { bottom: { style: BorderStyle.SINGLE, size: 6, color: C.line, space: 6 } } : undefined,
  children: [new TextRun({ text, font: FONT, size: o.size ?? 20, bold: o.bold,
    color: o.color ?? C.ink, italics: o.italics })]
});

// 여러 서식 조각을 한 문단에
const PR = (parts, o = {}) => new Paragraph({
  alignment: o.align, spacing: { before: o.before ?? 0, after: o.after ?? 100, line: 300 },
  indent: o.indent,
  children: parts.map(p => new TextRun({ text: p.t, font: FONT, size: p.size ?? o.size ?? 20,
    bold: p.b, color: p.c ?? C.ink, italics: p.i }))
});

const H1 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_1, spacing: { before: 380, after: 160 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 10, color: C.blue, space: 6 } },
  children: [new TextRun({ text, font: FONT, size: 28, bold: true, color: C.blue })]
});
const H2 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_2, spacing: { before: 260, after: 110 },
  children: [new TextRun({ text, font: FONT, size: 23, bold: true, color: C.ink })]
});
const H3 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_3, spacing: { before: 180, after: 80 },
  children: [new TextRun({ text, font: FONT, size: 21, bold: true, color: C.mid })]
});

const BULLET = (text, lvl = 0) => new Paragraph({
  numbering: { reference: 'bul', level: lvl },
  spacing: { after: 60, line: 290 },
  children: [new TextRun({ text, font: FONT, size: 20, color: C.ink })]
});
const NUM = (text, lvl = 0) => new Paragraph({
  numbering: { reference: 'num', level: lvl },
  spacing: { after: 60, line: 290 },
  children: [new TextRun({ text, font: FONT, size: 20, color: C.ink })]
});

const cell = (txt, w, o = {}) => new TableCell({
  width: { size: w, type: WidthType.DXA },
  shading: o.fill ? { type: ShadingType.CLEAR, fill: o.fill, color: 'auto' } : undefined,
  margins: { top: 60, bottom: 60, left: 90, right: 90 },
  verticalAlign: 'center',
  columnSpan: o.span,
  children: String(txt).split('\n').map(line => new Paragraph({
    alignment: o.align, spacing: { after: 0, line: 270 },
    children: [new TextRun({ text: line, font: FONT, size: o.size ?? 18,
      bold: o.bold, color: o.color ?? C.ink })]
  }))
});

/** rows[0] = header. widths in DXA, must sum to total. */
const TBL = (rows, widths, opt = {}) => {
  const total = widths.reduce((a, b) => a + b, 0);
  const alignOf = i => (opt.right && opt.right.includes(i)) ? AlignmentType.RIGHT
    : (opt.center && opt.center.includes(i)) ? AlignmentType.CENTER : AlignmentType.LEFT;
  return new Table({
    width: { size: total, type: WidthType.DXA },
    columnWidths: widths,
    borders: {
      top: { style: BorderStyle.SINGLE, size: 6, color: C.line },
      bottom: { style: BorderStyle.SINGLE, size: 6, color: C.line },
      left: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
      right: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
      insideHorizontal: { style: BorderStyle.SINGLE, size: 4, color: C.line },
      insideVertical: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' }
    },
    rows: rows.map((r, ri) => new TableRow({
      tableHeader: ri === 0,
      children: r.map((c, ci) => cell(c, widths[ci], {
        fill: ri === 0 ? C.head : (opt.zebra && ri % 2 === 0 ? C.zebra : undefined),
        bold: ri === 0 || (opt.boldRows && opt.boldRows.includes(ri)),
        align: ri === 0 ? (ci === 0 ? AlignmentType.LEFT : alignOf(ci)) : alignOf(ci),
        size: opt.size ?? 17,
        color: ri === 0 ? C.mid : undefined
      }))
    }))
  });
};

const SPACER = (h = 120) => new Paragraph({ spacing: { after: h }, children: [] });

// 강조 박스 (좌측 컬러 바 + 배경)
const BOX = (title, body, tone = 'blue') => {
  const col = { blue: C.blue, green: C.green, amber: C.amber, red: C.red }[tone];
  const fill = { blue: 'F0F4FB', green: 'EFF6F2', amber: 'FBF5E9', red: 'FBF0F0' }[tone];
  return new Table({
    width: { size: 9360, type: WidthType.DXA }, columnWidths: [9360],
    borders: {
      top: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
      bottom: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
      right: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
      left: { style: BorderStyle.SINGLE, size: 18, color: col },
      insideHorizontal: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
      insideVertical: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' }
    },
    rows: [new TableRow({
      children: [new TableCell({
        width: { size: 9360, type: WidthType.DXA },
        shading: { type: ShadingType.CLEAR, fill, color: 'auto' },
        margins: { top: 120, bottom: 120, left: 160, right: 140 },
        children: [
          new Paragraph({ spacing: { after: 60, line: 290 },
            children: [new TextRun({ text: title, font: FONT, size: 20, bold: true, color: col })] }),
          ...body.map(t => new Paragraph({ spacing: { after: 40, line: 290 },
            children: [new TextRun({ text: t, font: FONT, size: 18, color: C.ink })] }))
        ]
      })]
    })]
  });
};

const numbering = {
  config: [
    { reference: 'bul', levels: [
      { level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 360, hanging: 200 } },
                 run: { font: FONT, size: 20 } } },
      { level: 1, format: LevelFormat.BULLET, text: '–', alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 200 } },
                 run: { font: FONT, size: 20 } } }
    ]},
    { reference: 'num', levels: [
      { level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 380, hanging: 240 } },
                 run: { font: FONT, size: 20 } } }
    ]}
  ]
};

const styles = {
  default: { document: { run: { font: FONT, size: 20, color: C.ink }, paragraph: { spacing: { line: 300 } } } },
  paragraphStyles: [
    { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
      run: { font: FONT, size: 28, bold: true, color: C.blue } },
    { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
      run: { font: FONT, size: 23, bold: true, color: C.ink } },
    { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true,
      run: { font: FONT, size: 21, bold: true, color: C.mid } }
  ]
};

const pageSection = (docTitle) => ({
  properties: { page: { margin: { top: 1200, right: 1080, bottom: 1100, left: 1080 } } },
  headers: { default: new Header({ children: [new Paragraph({
    alignment: AlignmentType.RIGHT, spacing: { after: 0 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: C.line, space: 4 } },
    children: [new TextRun({ text: docTitle, font: FONT, size: 15, color: C.mute })] })] }) },
  footers: { default: new Footer({ children: [new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 15, color: C.mute })] })] }) }
});

const COVER = (title, subtitle, meta) => ([
  new Paragraph({ spacing: { before: 2200, after: 0 }, children: [] }),
  new Paragraph({ alignment: AlignmentType.LEFT, spacing: { after: 260, line: 300 },
    children: [new TextRun({ text: 'FreeFlexVPN', font: FONT, size: 22, bold: true, color: C.blue })] }),
  new Paragraph({ alignment: AlignmentType.LEFT, spacing: { after: 200, line: 640 },
    children: [new TextRun({ text: title, font: FONT, size: 52, bold: true, color: C.ink })] }),
  new Paragraph({ alignment: AlignmentType.LEFT, spacing: { after: 400 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: C.blue, space: 10 } },
    children: [new TextRun({ text: subtitle, font: FONT, size: 22, color: C.mid })] }),
  ...meta.map(m => new Paragraph({ spacing: { after: 60 },
    children: [
      new TextRun({ text: m[0] + '   ', font: FONT, size: 18, color: C.mute }),
      new TextRun({ text: m[1], font: FONT, size: 18, color: C.ink, bold: true })
    ] })),
  new Paragraph({ children: [new PageBreak()] })
]);

module.exports = { d, Document, Packer, Paragraph, TextRun, AlignmentType, HeadingLevel,
  P, PR, H1, H2, H3, BULLET, NUM, TBL, BOX, SPACER, COVER, numbering, styles, pageSection,
  TableOfContents, PageBreak, FONT, C };
