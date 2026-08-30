
export interface AnnotatedWord {
  word: string;
  phonetic: string;
  meaning: string;
  example: string;
  audio?: string;
  learning?: boolean;
  kind?: 'word' | 'phrase' | 'chunk';
  start?: number;
  end?: number;
}

export interface HiddenWord {
  start: number;
  end: number;
  word: string;
}

interface LegacyHiddenWord {
  index: number;
  word: string;
}

export interface ArticleSentence {
  id: string;
  text: string;
  translation: string;
  startTime?: number;
  endTime?: number;
  words: AnnotatedWord[];
  hiddenWords?: Array<HiddenWord | LegacyHiddenWord>;
}

const normalizeHiddenWords = (
  sentenceText: string,
  hiddenWords?: Array<HiddenWord | LegacyHiddenWord>
): HiddenWord[] => {
  if (!hiddenWords?.length) {
    return [];
  }

  const tokenRanges = Array.from(sentenceText.matchAll(/\S+/g)).map((match) => ({
    start: match.index ?? 0,
    end: (match.index ?? 0) + match[0].length,
  }));

  return hiddenWords.map((hiddenWord) => {
    if ('start' in hiddenWord && 'end' in hiddenWord) {
      return {
        start: hiddenWord.start,
        end: hiddenWord.end,
        word: hiddenWord.word,
      };
    }

    const range = tokenRanges[hiddenWord.index];

    return {
      start: range?.start ?? 0,
      end: range?.end ?? sentenceText.length,
      word: hiddenWord.word,
    };
  });
};

export class ArticleParagraph {
  id: string;
  sentences: ArticleSentence[];

  constructor(data: { id: string; sentences: ArticleSentence[] }) {
    this.id = data.id;
    this.sentences = data.sentences;
  }

  get text(): string {
    return this.sentences.map((sentence) => sentence.text).join(' ');
  }
}

export interface Article {
  id: string;
  audioUrl: string;
  title: string;
  summary: string;
  readingSummary: string;
  difficulty: string;
  duration: string;
  tags: string[];
  thumbLarge: string;
  superJumbo: string;
  image?: string;
  questions: {
    id: string;
    question: string;
    answer: string;
  }[];
  content: {
    paragraphs: ArticleParagraph[];
  };
}

type RawArticle = Omit<Article, 'content'> & {
  content: {
    paragraphs: { id: string; sentences: ArticleSentence[] }[];
  };
};

const rawMockArticles: RawArticle[] = [
  {
  "id": "1",
  "audioUrl": "src/data/Steady_pvc_sp100.mp3",
  "title": "Should a Judge Rule on His Own Case?",
  "summary": "这篇文章说明，医生并不总是完全公正和理性，隐藏的偏见会影响他们的治疗判断，并导致严重错误。",
  "readingSummary": "Doctors are not always fair or logical. This article shows how hidden bias can shape medical choices and lead to serious mistakes. It explains why even experts can make poor decisions.",
  "difficulty": "B2",
  "duration": "4 min",
  "tags": ["健康", "医学", "认知"],
  "thumbLarge": "https://static01.nyt.com/images/2016/03/01/opinion/01tue4web/01tue4web-thumbLarge.jpg",
  "superJumbo": "https://static01.nyt.com/images/2016/03/01/opinion/01tue4web/01tue4web-superJumbo.jpg",
  "questions": [
    {
      "id": "q1",
      "question": "Why can doctors make bad decisions even when they are experts?",
      "answer": "Because hidden bias can affect how they think and choose treatment."
    },
    {
      "id": "q2",
      "question": "What is one example of bias in medicine mentioned in the article?",
      "answer": "Black patients were less likely than white patients to receive pain medication in the emergency department."
    }
  ],
  "content": {
    "paragraphs": [
      {
        "id": "p1",
        "sentences": [
          {
            "id": "s1",
            "text": "It’s tempting to believe that physicians are logical, meticulous thinkers who perfectly weigh the pros and cons of treatment options, acting as unbiased surrogates for their patients.",
            "translation": "人们很容易相信，医生是逻辑清晰、一丝不苟的思考者，能够完美地权衡治疗方案的利弊，作为毫无偏见的代理人替患者做出决定。",
              "startTime": 0,
              "endTime": 11.88,
            "words": [
              {
                "word": "tempting",
                "start": 5,
                "end": 13,
                "phonetic": "/ˈtɛmptɪŋ/",
                "meaning": "诱人的；令人想做的",
                "example": "It is tempting to skip the gym.",
                "learning": true,
                "kind": "word"
              },
              {
                "word": "meticulous",
                "start": 54,
                "end": 64,
                "phonetic": "/məˈtɪkjələs/",
                "meaning": "一丝不苟的",
                "example": "She made a meticulous plan.",
                "learning": true,
                "kind": "word"
              }
            ],
            "hiddenWords": [
              { "start": 5, "end": 13, "word": "tempting" },
              { "start": 30, "end": 40, "word": "physicians" },
              { "start": 45, "end": 53, "word": "logical," },
              { "start": 54, "end": 64, "word": "meticulous" },
              { "start": 88, "end": 93, "word": "weigh" },
              { "start": 98, "end": 102, "word": "pros" },
              { "start": 107, "end": 111, "word": "cons" },
              { "start": 115, "end": 124, "word": "treatment" },
              { "start": 153, "end": 163, "word": "surrogates" }
            ]
          }
        ]
      },
      {
        "id": "p2",
        "sentences": [
          {
            "id": "s2",
            "text": "In reality, this is often far from the case.",
            "translation": "然而，现实中情况往往远非如此。",
            "startTime": 11.88,
            "endTime": 15.76,
            "words": [
              {
                "word": "reality",
                "start": 3,
                "end": 10,
                "phonetic": "/riˈæləti/",
                "meaning": "现实",
                "example": "In reality, it was different.",
                "learning": true,
                "kind": "word"
              }
            ],
            "hiddenWords": [
              { "start": 3, "end": 11, "word": "reality," },
              { "start": 26, "end": 29, "word": "far" },
              { "start": 39, "end": 44, "word": "case." }
            ]
          },
          {
            "id": "s3",
            "text": "Bias, which takes many forms, affects how doctors think and the treatment decisions they make.",
            "translation": "偏见有多种形式，会影响医生的思维方式以及他们做出的治疗决定。",
            "startTime": 15.76,
            "endTime": 22.48,
            "words": [
              {
                "word": "bias",
                "start": 0,
                "end": 4,
                "phonetic": "/ˈbaɪəs/",
                "meaning": "偏见",
                "example": "There is a bias against older workers.",
                "learning": true,
                "kind": "word"
              },
              {
                "word": "treatment",
                "start": 64,
                "end": 73,
                "phonetic": "/ˈtriːtmənt/",
                "meaning": "治疗",
                "example": "The treatment worked well.",
                "learning": true,
                "kind": "word"
              }
            ],
            "hiddenWords": [
              { "start": 0, "end": 5, "word": "Bias," },
              { "start": 30, "end": 37, "word": "affects" },
              { "start": 42, "end": 49, "word": "doctors" },
              { "start": 64, "end": 73, "word": "treatment" },
              { "start": 74, "end": 83, "word": "decisions" }
            ]
          }
        ]
      },
      {
        "id": "p3",
        "sentences": [
          {
            "id": "s4",
            "text": "Racial biases in treatment decisions by physicians are well documented.",
            "translation": "医生在治疗决定中存在的种族偏见已有充分记录。",
            "startTime": 22.48,
            "endTime": 27.8,
            "words": [
              {
                "word": "racial",
                "start": 0,
                "end": 6,
                "phonetic": "/ˈreɪʃəl/",
                "meaning": "种族的",
                "example": "Racial equality matters.",
                "learning": true,
                "kind": "word"
              }
            ],
            "hiddenWords": [
              { "start": 0, "end": 6, "word": "Racial" },
              { "start": 7, "end": 13, "word": "biases" },
              { "start": 40, "end": 50, "word": "physicians" },
              { "start": 60, "end": 71, "word": "documented." }
            ]
          },
          {
            "id": "s5",
            "text": "One study found that black patients were significantly less likely than white patients to receive pain medication in the emergency department, despite reporting similar levels of pain.",
            "translation": "一项研究发现，尽管黑人患者报告的疼痛程度与白人患者相似，但他们在急诊科获得止痛药的可能性却明显更低。",
            "startTime": 27.84,
            "endTime": 36.32,
            "words": [
              {
                "word": "pain medication",
                "start": 98,
                "end": 113,
                "phonetic": "/peɪn məˌdɪkeɪʃən/",
                "meaning": "止痛药",
                "example": "She took pain medication after surgery.",
                "learning": true,
                "kind": "phrase"
              },
              {
                "word": "emergency department",
                "start": 121,
                "end": 141,
                "phonetic": "/ɪˈmɜːdʒənsi dɪˈpɑːtmənt/",
                "meaning": "急诊科",
                "example": "He went to the emergency department.",
                "learning": true,
                "kind": "phrase"
              }
            ],
            "hiddenWords": [
              { "start": 4, "end": 9, "word": "study" },
              { "start": 21, "end": 26, "word": "black" },
              { "start": 27, "end": 35, "word": "patients" },
              { "start": 41, "end": 54, "word": "significantly" },
              { "start": 72, "end": 77, "word": "white" },
              { "start": 90, "end": 97, "word": "receive" },
              { "start": 98, "end": 102, "word": "pain" },
              { "start": 103, "end": 113, "word": "medication" },
              { "start": 121, "end": 130, "word": "emergency" },
              { "start": 179, "end": 184, "word": "pain." }
            ]
          },
          {
            "id": "s6",
            "text": "Other research suggests that longstanding racial biases among providers might have contributed to racial differences in patient trust in the health system.",
            "translation": "其他研究表明，医疗提供者长期存在的种族偏见，可能导致了不同种族患者在信任医疗系统方面存在差异。",
            "startTime": 62.6,
            "endTime": 75.4,
            "words": [
              {
                "word": "longstanding",
                "start": 29,
                "end": 41,
                "phonetic": "/ˈlɒŋstændɪŋ/",
                "meaning": "长期存在的",
                "example": "There is a longstanding tradition.",
                "learning": true,
                "kind": "word"
              }
            ],
            "hiddenWords": [
              { "start": 6, "end": 14, "word": "research" },
              { "start": 29, "end": 41, "word": "longstanding" },
              { "start": 49, "end": 55, "word": "biases" },
              { "start": 62, "end": 71, "word": "providers" },
              { "start": 83, "end": 94, "word": "contributed" },
              { "start": 128, "end": 133, "word": "trust" },
              { "start": 141, "end": 147, "word": "health" },
              { "start": 148, "end": 155, "word": "system." }
            ]
          }
        ]
      },
      {
        "id": "p4",
        "sentences": [
          {
            "id": "s7",
            "text": "But a growing body of scientific research on physician decision-making shows that doctors exhibit other biases as well — cognitive ones — that influence the way they think and treat patients.",
            "translation": "但越来越多关于医生决策的科学研究表明，医生还会表现出其他偏见——即认知偏见——这些偏见会影响他们的思维方式和对待患者的方式。",
            "startTime": 36.32,
            "endTime": 49.28,
            "words": [
              {
                "word": "scientific",
                "start": 22,
                "end": 32,
                "phonetic": "/ˌsaɪənˈtɪfɪk/",
                "meaning": "科学的",
                "example": "We need scientific evidence.",
                "learning": true,
                "kind": "word"
              },
              {
                "word": "cognitive",
                "start": 121,
                "end": 130,
                "phonetic": "/ˈkɒɡnətɪv/",
                "meaning": "认知的",
                "example": "Cognitive skills improve with practice.",
                "learning": true,
                "kind": "word"
              }
            ],
            "hiddenWords": [
              { "start": 22, "end": 32, "word": "scientific" },
              { "start": 33, "end": 41, "word": "research" },
              { "start": 45, "end": 54, "word": "physician" },
              { "start": 55, "end": 70, "word": "decision-making" },
              { "start": 82, "end": 89, "word": "doctors" },
              { "start": 104, "end": 110, "word": "biases" },
              { "start": 121, "end": 130, "word": "cognitive" },
              { "start": 143, "end": 152, "word": "influence" },
              { "start": 176, "end": 181, "word": "treat" },
              { "start": 182, "end": 191, "word": "patients." }
            ]
          },
          {
            "id": "s8",
            "text": "These biases lead doctors to make the same mistakes as the rest of us, but usually at a greater cost.",
            "translation": "这些偏见会使医生犯下和我们其他人一样的错误，但通常代价更大。",
            "startTime": 49.28,
            "endTime": 62.6,
            "words": [
              {
                "word": "serious",
                "phonetic": "/ˈsɪəriəs/",
                "meaning": "严重的",
                "example": "This is a serious problem.",
                "learning": true,
                "kind": "word"
              }
            ],
            "hiddenWords": [
              { "start": 6, "end": 12, "word": "biases" },
              { "start": 18, "end": 25, "word": "doctors" },
              { "start": 43, "end": 51, "word": "mistakes" },
              { "start": 75, "end": 82, "word": "usually" },
              { "start": 88, "end": 95, "word": "greater" },
              { "start": 96, "end": 101, "word": "cost." }
            ]
          }
        ]
      },
      {
        "id": "p5",
        "sentences": [
          {
            "id": "s11",
            "text": "Cognitive biases refer to a range of systematic errors in human decision-making stemming from the tendency to use mental shortcuts.",
            "translation": "认知偏见指的是人类决策过程中一系列系统性的错误，这些错误源于人们倾向于使用心理捷径。",
            "startTime": 62.6,
            "endTime": 70.16,
            "words": [
              {
                "word": "systematic",
                "start": 37,
                "end": 47,
                "phonetic": "/ˌsɪstəˈmætɪk/",
                "meaning": "系统性的",
                "example": "The study used a systematic method.",
                "learning": true,
                "kind": "word"
              },
              {
                "word": "mental shortcuts",
                "start": 114,
                "end": 130,
                "phonetic": "/ˈmentl ˈʃɔːrtkʌts/",
                "meaning": "心理捷径",
                "example": "We often use mental shortcuts.",
                "learning": true,
                "kind": "phrase"
              }
            ],
            "hiddenWords": [
              { "start": 0, "end": 9, "word": "Cognitive" },
              { "start": 37, "end": 47, "word": "systematic" },
              { "start": 48, "end": 54, "word": "errors" },
              { "start": 58, "end": 63, "word": "human" },
              { "start": 64, "end": 79, "word": "decision-making" },
              { "start": 98, "end": 106, "word": "tendency" },
              { "start": 121, "end": 131, "word": "shortcuts." }
            ]
          }
        ]
      },
      {
        "id": "p6",
        "sentences": [
          {
            "id": "s9",
            "text": "Prominent examples include confirmation bias, the tendency to interpret new information in a way favorable to one’s preconceptions; and anchoring, the tendency to overly weight an initial piece of information, even when order does not matter.",
            "translation": "典型的例子包括确认偏见，即倾向于以有利于自己先入之见的方式解释新信息；以及锚定效应，即过度重视最初获得的信息，即使先后顺序并不重要。",
            "startTime": 70.16,
            "endTime": 79.32,
            "words": [
              {
                "word": "confirmation bias",
                "start": 27,
                "end": 44,
                "phonetic": "/kənˌfɜːrˈmeɪʃən ˈbaɪəs/",
                "meaning": "确认偏见",
                "example": "Confirmation bias can block new ideas.",
                "learning": true,
                "kind": "phrase"
              }
            ],
            "hiddenWords": [
              { "start": 0, "end": 9, "word": "Prominent" },
              { "start": 10, "end": 18, "word": "examples" },
              { "start": 27, "end": 39, "word": "confirmation" },
              { "start": 40, "end": 45, "word": "bias," },
              { "start": 62, "end": 71, "word": "interpret" },
              { "start": 76, "end": 87, "word": "information" },
              { "start": 97, "end": 106, "word": "favorable" },
              { "start": 116, "end": 131, "word": "preconceptions;" },
              { "start": 136, "end": 146, "word": "anchoring," },
              { "start": 170, "end": 176, "word": "weight" },
              { "start": 180, "end": 187, "word": "initial" },
              { "start": 197, "end": 209, "word": "information," },
              { "start": 235, "end": 242, "word": "matter." }
            ]
          },
          {
            "id": "s10",
            "text": "Anchoring helps explain why if you see a car priced at $20,000 and a second car priced at $8,000, you might conclude the second car is cheap, whereas if the first car cost $3,000 you might conclude that the second car is expensive.",
            "translation": "锚定效应有助于解释：如果你看到一辆标价2万美元的汽车和另一辆标价8000美元的汽车，你可能会觉得第二辆车很便宜；但如果第一辆车只值3000美元，你则可能会觉得第二辆车很贵。",
            "startTime": 79.32,
            "endTime": 95.84,
            "words": [
              {
                "word": "anchoring",
                "start": 0,
                "end": 9,
                "phonetic": "/ˈæŋkərɪŋ/",
                "meaning": "锚定效应",
                "example": "Anchoring can change our judgment.",
                "learning": true,
                "kind": "word"
              }
            ],
            "hiddenWords": [
              { "start": 0, "end": 9, "word": "Anchoring" },
              { "start": 10, "end": 15, "word": "helps" },
              { "start": 16, "end": 23, "word": "explain" },
              { "start": 41, "end": 44, "word": "car" },
              { "start": 55, "end": 62, "word": "$20,000" },
              { "start": 69, "end": 75, "word": "second" },
              { "start": 90, "end": 97, "word": "$8,000," },
              { "start": 108, "end": 116, "word": "conclude" },
              { "start": 135, "end": 141, "word": "cheap," },
              { "start": 157, "end": 162, "word": "first" },
              { "start": 172, "end": 178, "word": "$3,000" },
              { "start": 189, "end": 197, "word": "conclude" },
              { "start": 221, "end": 231, "word": "expensive." }
            ]
          }
        ]
      }
    ]
  }
},
  {
    id: '2',
    audioUrl: '/audio/article2.mp3',
    title: '全球气候变化的挑战',
    summary: '了解当前全球变暖的现状及其对生态系统的深远影响。',
    readingSummary: 'Doctors are not always fully logical. They can have racial and thinking biases that affect how they treat patients. For example, Black patients may get less pain medicine. Doctors also make cognitive mistakes like favoring first information or fitting facts to their beliefs. These biases change medical decisions and can hurt patients.',
    difficulty: 'C1',
    duration: '8 min',
    tags: ['自然', '时政'],
    thumbLarge: 'https://images.unsplash.com/photo-1559827260-dc66d52bef19?w=400&h=300&fit=crop&quality=75',
    superJumbo: 'https://images.unsplash.com/photo-1559827260-dc66d52bef19?w=1200&h=800&fit=crop&quality=80',
    content: {
      paragraphs: [
        {
          id: 'p1',
          sentences: [
            {
              id: 's1',
              text: 'Climate change is one of the greatest challenges facing humanity today.',
              translation: '气候变化是当今人类面临的最大挑战之一。',
              startTime: 0,
              endTime: 8.24,
              words: [
                { word: 'humanity', phonetic: '/hjuːˈmænəti/', meaning: '人类', example: 'The future of humanity is at stake.' }
              ],
              hiddenWords: [
                { index: 0, word: 'Climate' },
                { index: 6, word: 'greatest' },
                { index: 7, word: 'challenges' },
                { index: 9, word: 'humanity' }
              ]
            }
          ]
        }
      ]
    },
    questions: []
  },
  {
    id: '3',
    audioUrl: '/audio/article3.mp3',
    title: '数字时代的社交媒体',
    summary: '探讨社交媒体如何改变了我们的沟通方式及心理健康。',
    readingSummary: 'Social media has revolutionized the way we connect with others. It has also raised concerns about its impact on mental health and well-being.',
    difficulty: 'B2',
    duration: '4 min',
    tags: ['社会', '心理'],
    thumbLarge: 'https://images.unsplash.com/photo-1611532736579-6b16e2b50449?w=400&h=300&fit=crop&quality=75',
    superJumbo: 'https://images.unsplash.com/photo-1611532736579-6b16e2b50449?w=1200&h=800&fit=crop&quality=80',
    content: {
      paragraphs: [
        {
          id: 'p1',
          sentences: [
            {
              id: 's1',
              text: 'Social media has revolutionized the way we connect with others.',
              translation: '社交媒体彻底改变了我们与他人联系的方式。',
              startTime: 0,
              endTime: 8.12,
              words: [
                { word: 'revolutionized', phonetic: '/ˌrevəˈluːʃənaɪzd/', meaning: '彻底改革', example: 'The Internet has revolutionized communication.' }
              ],
              hiddenWords: [
                { index: 0, word: 'Social' },
                { index: 1, word: 'media' },
                { index: 3, word: 'revolutionized' },
                { index: 7, word: 'connect' }
              ]
            }
          ]
        }
      ]
    },
    questions: []
  }
];

export const mockArticles: Article[] = rawMockArticles.map((article) => ({
  ...article,
  content: {
    paragraphs: article.content.paragraphs.map((paragraph) => new ArticleParagraph({
      id: paragraph.id,
      sentences: paragraph.sentences.map((sentence) => ({
        ...sentence,
        hiddenWords: normalizeHiddenWords(sentence.text, sentence.hiddenWords),
      })),
    })),
  },
}));
