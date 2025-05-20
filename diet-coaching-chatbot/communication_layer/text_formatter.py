import re
import itertools
from communication_layer.communicator import Communicator


class TextFormatterUtility:
    char_format_table = {
        'target': ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J',
                   'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '!', '?', '.', ',', '"', "'"],
        'serifBold': ['𝐚', '𝐛', '𝐜', '𝐝', '𝐞', '𝐟', '𝐠', '𝐡', '𝐢', '𝐣', '𝐤', '𝐥', '𝐦', '𝐧', '𝐨', '𝐩', '𝐪', '𝐫', '𝐬', '𝐭', '𝐮', '𝐯', '𝐰', '𝐱', '𝐲', '𝐳', '𝐀', '𝐁', '𝐂',
                      '𝐃', '𝐄', '𝐅', '𝐆', '𝐇', '𝐈', '𝐉', '𝐊', '𝐋', '𝐌', '𝐍', '𝐎', '𝐏', '𝐐', '𝐑', '𝐒', '𝐓', '𝐔', '𝐕', '𝐖', '𝐗', '𝐘', '𝐙', '𝟎', '𝟏', '𝟐', '𝟑', '𝟒', '𝟓',
                      '𝟔', '𝟕', '𝟖', '𝟗', '❗', '❓', '.', ',', '"', "'"],
        'serifItalic': ['𝑎', '𝑏', '𝑐', '𝑑', '𝑒', '𝑓', '𝑔', 'ℎ', '𝑖', '𝑗', '𝑘', '𝑙', '𝑚', '𝑛', '𝑜', '𝑝', '𝑞', '𝑟', '𝑠', '𝑡', '𝑢', '𝑣', '𝑤', '𝑥', '𝑦', '𝑧', '𝐴', '𝐵', '𝐶',
                        '𝐷', '𝐸', '𝐹', '𝐺', '𝐻', '𝐼', '𝐽', '𝐾', '𝐿', '𝑀', '𝑁', '𝑂', '𝑃', '𝑄', '𝑅', '𝑆', '𝑇', '𝑈', '𝑉', '𝑊', '𝑋', '𝑌', '𝑍', '0', '1', '2', '3', '4', '5', '6',
                        '7', '8', '9', '!', '?', '.', ',', '"', "'"],
        'serifBoldItalic': ['𝒂', '𝒃', '𝒄', '𝒅', '𝒆', '𝒇', '𝒈', '𝒉', '𝒊', '𝒋', '𝒌', '𝒍', '𝒎', '𝒏', '𝒐', '𝒑', '𝒒', '𝒓', '𝒔', '𝒕', '𝒖', '𝒗', '𝒘', '𝒙', '𝒚', '𝒛', '𝑨', '𝑩',
                            '𝑪', '𝑫', '𝑬', '𝑭', '𝑮', '𝑯', '𝑰', '𝑱', '𝑲', '𝑳', '𝑴', '𝑵', '𝑶', '𝑷', '𝑸', '𝑹', '𝑺', '𝑻', '𝑼', '𝑽', '𝑾', '𝑿', '𝒀', '𝒁', '𝟎', '𝟏', '𝟐', '𝟑',
                            '𝟒', '𝟓', '𝟔', '𝟕', '𝟖', '𝟗', '❗', '❓', '.', ',', '"', "'"],
        'sansItalic': ['𝘢', '𝘣', '𝘤', '𝘥', '𝘦', '𝘧', '𝘨', '𝘩', '𝘪', '𝘫', '𝘬', '𝘭', '𝘮', '𝘯', '𝘰', '𝘱', '𝘲', '𝘳', '𝘴', '𝘵', '𝘶', '𝘷', '𝘸', '𝘹', '𝘺', '𝘻', '𝘈', '𝘉', '𝘊',
                       '𝘋', '𝘌', '𝘍', '𝘎', '𝘏', '𝘐', '𝘑', '𝘒', '𝘓', '𝘔', '𝘕', '𝘖', '𝘗', '𝘘', '𝘙', '𝘚', '𝘛', '𝘜', '𝘝', '𝘞', '𝘟', '𝘠', '𝘡', '0', '1', '2', '3', '4', '5', '6', '7',
                       '8', '9', '!', '?', '.', ',', '"', "'"],
        'sansBoldItalic': ['𝙖', '𝙗', '𝙘', '𝙙', '𝙚', '𝙛', '𝙜', '𝙝', '𝙞', '𝙟', '𝙠', '𝙡', '𝙢', '𝙣', '𝙤', '𝙥', '𝙦', '𝙧', '𝙨', '𝙩', '𝙪', '𝙫', '𝙬', '𝙭', '𝙮', '𝙯', '𝘼', '𝘽', '𝘾',
                           '𝘿', '𝙀', '𝙁', '𝙂', '𝙃', '𝙄', '𝙅', '𝙆', '𝙇', '𝙈', '𝙉', '𝙊', '𝙋', '𝙌', '𝙍', '𝙎', '𝙏', '𝙐', '𝙑', '𝙒', '𝙓', '𝙔', '𝙕', '𝟎', '𝟏', '𝟐', '𝟑', '𝟒', '𝟓',
                           '𝟔', '𝟕', '𝟖', '𝟗', '❗', '❓', '.', ',', '"', "'"],
        'sansBold': ['𝗮', '𝗯', '𝗰', '𝗱', '𝗲', '𝗳', '𝗴', '𝗵', '𝗶', '𝗷', '𝗸', '𝗹', '𝗺', '𝗻', '𝗼', '𝗽', '𝗾', '𝗿', '𝘀', '𝘁', '𝘂', '𝘃', '𝘄', '𝘅', '𝘆', '𝘇', '𝗔', '𝗕', '𝗖', '𝗗',
                     '𝗘', '𝗙', '𝗚', '𝗛', '𝗜', '𝗝', '𝗞', '𝗟', '𝗠', '𝗡', '𝗢', '𝗣', '𝗤', '𝗥', '𝗦', '𝗧', '𝗨', '𝗩', '𝗪', '𝗫', '𝗬', '𝗭', '𝟬', '𝟭', '𝟮', '𝟯', '𝟰', '𝟱', '𝟲', '𝟳',
                     '𝟴', '𝟵', '❗', '❓', '.', ',', '"', "'"],
        'sans': ['𝖺', '𝖻', '𝖼', '𝖽', '𝖾', '𝖿', '𝗀', '𝗁', '𝗂', '𝗃', '𝗄', '𝗅', '𝗆', '𝗇', '𝗈', '𝗉', '𝗊', '𝗋', '𝗌', '𝗍', '𝗎', '𝗏', '𝗐', '𝗑', '𝗒', '𝗓', '𝖠', '𝖡', '𝖢', '𝖣',
                 '𝖤', '𝖥', '𝖦', '𝖧', '𝖨', '𝖩', '𝖪', '𝖫', '𝖬', '𝖭', '𝖮', '𝖯', '𝖰', '𝖱', '𝖲', '𝖳', '𝖴', '𝖵', '𝖶', '𝖷', '𝖸', '𝖹', '𝟢', '𝟣', '𝟤', '𝟥', '𝟦', '𝟧', '𝟨', '𝟩',
                 '𝟪', '𝟫', '!', '?', '.', ',', '"', "'"],
        'scriptBold': ['𝓪', '𝓫', '𝓬', '𝓭', '𝓮', '𝓯', '𝓰', '𝓱', '𝓲', '𝓳', '𝓴', '𝓵', '𝓶', '𝓷', '𝓸', '𝓹', '𝓺', '𝓻', '𝓼', '𝓽', '𝓾', '𝓿', '𝔀', '𝔁', '𝔂', '𝔃', '𝓐', '𝓑', '𝓒',
                       '𝓓', '𝓔', '𝓕', '𝓖', '𝓗', '𝓘', '𝓙', '𝓚', '𝓛', '𝓜', '𝓝', '𝓞', '𝓟', '𝓠', '𝓡', '𝓢', '𝓣', '𝓤', '𝓥', '𝓦', '𝓧', '𝓨', '𝓩', '𝟎', '𝟏', '𝟐', '𝟑', '𝟒', '𝟓',
                       '𝟔', '𝟕', '𝟖', '𝟗', '❗', '❓', '.', ',', '"', "'"],
        'script': ['𝒶', '𝒷', '𝒸', '𝒹', 'ℯ', '𝒻', 'ℊ', '𝒽', '𝒾', '𝒿', '𝓀', '𝓁', '𝓂', '𝓃', 'ℴ', '𝓅', '𝓆', '𝓇', '𝓈', '𝓉', '𝓊', '𝓋', '𝓌', '𝓍', '𝓎', '𝓏', '𝒜', 'ℬ', '𝒞', '𝒟', 'ℰ',
                   'ℱ', '𝒢', 'ℋ', 'ℐ', '𝒥', '𝒦', 'ℒ', 'ℳ', '𝒩', '𝒪', '𝒫', '𝒬', 'ℛ', '𝒮', '𝒯', '𝒰', '𝒱', '𝒲', '𝒳', '𝒴', '𝒵', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '!', '?',
                   '.', ',', '"', "'"],
        'frakturBold': ['𝖆', '𝖇', '𝖈', '𝖉', '𝖊', '𝖋', '𝖌', '𝖍', '𝖎', '𝖏', '𝖐', '𝖑', '𝖒', '𝖓', '𝖔', '𝖕', '𝖖', '𝖗', '𝖘', '𝖙', '𝖚', '𝖛', '𝖜', '𝖝', '𝖞', '𝖟', '𝕬', '𝕭', '𝕮',
                        '𝕯', '𝕰', '𝕱', '𝕲', '𝕳', '𝕴', '𝕵', '𝕶', '𝕷', '𝕸', '𝕹', '𝕺', '𝕻', '𝕼', '𝕽', '𝕾', '𝕿', '𝖀', '𝖁', '𝖂', '𝖃', '𝖄', '𝖅', '𝟎', '𝟏', '𝟐', '𝟑', '𝟒', '𝟓',
                        '𝟔', '𝟕', '𝟖', '𝟗', '❗', '❓', '.', ',', '"', "'"],
        'fraktur': ['𝔞', '𝔟', '𝔠', '𝔡', '𝔢', '𝔣', '𝔤', '𝔥', '𝔦', '𝔧', '𝔨', '𝔩', '𝔪', '𝔫', '𝔬', '𝔭', '𝔮', '𝔯', '𝔰', '𝔱', '𝔲', '𝔳', '𝔴', '𝔵', '𝔶', '𝔷', '𝔄', '𝔅', 'ℭ', '𝔇',
                    '𝔈', '𝔉', '𝔊', 'ℌ', 'ℑ', '𝔍', '𝔎', '𝔏', '𝔐', '𝔑', '𝔒', '𝔓', '𝔔', 'ℜ', '𝔖', '𝔗', '𝔘', '𝔙', '𝔚', '𝔛', '𝔜', 'ℨ', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
                    '!', '?', '.', ',', '"', "'"],
        'monospace': ['𝚊', '𝚋', '𝚌', '𝚍', '𝚎', '𝚏', '𝚐', '𝚑', '𝚒', '𝚓', '𝚔', '𝚕', '𝚖', '𝚗', '𝚘', '𝚙', '𝚚', '𝚛', '𝚜', '𝚝', '𝚞', '𝚟', '𝚠', '𝚡', '𝚢', '𝚣', '𝙰', '𝙱', '𝙲',
                      '𝙳', '𝙴', '𝙵', '𝙶', '𝙷', '𝙸', '𝙹', '𝙺', '𝙻', '𝙼', '𝙽', '𝙾', '𝙿', '𝚀', '𝚁', '𝚂', '𝚃', '𝚄', '𝚅', '𝚆', '𝚇', '𝚈', '𝚉', '𝟶', '𝟷', '𝟸', '𝟹', '𝟺', '𝟻',
                      '𝟼', '𝟽', '𝟾', '𝟿', '！', '？', '．', '，', '"', '＇'],
        'fullwidth': ['ａ', 'ｂ', 'ｃ', 'ｄ', 'ｅ', 'ｆ', 'ｇ', 'ｈ', 'ｉ', 'ｊ', 'ｋ', 'ｌ', 'ｍ', 'ｎ', 'ｏ', 'ｐ', 'ｑ', 'ｒ', 'ｓ', 'ｔ', 'ｕ', 'ｖ', 'ｗ', 'ｘ', 'ｙ', 'ｚ', 'Ａ', 'Ｂ', 'Ｃ', 'Ｄ', 'Ｅ', 'Ｆ', 'Ｇ', 'Ｈ', 'Ｉ',
                      'Ｊ', 'Ｋ', 'Ｌ', 'Ｍ', 'Ｎ', 'Ｏ', 'Ｐ', 'Ｑ', 'Ｒ', 'Ｓ', 'Ｔ', 'Ｕ', 'Ｖ', 'Ｗ', 'Ｘ', 'Ｙ', 'Ｚ', '０', '１', '２', '３', '４', '５', '６', '７', '８', '９', '！', '？', '．', '，', '"', '＇'],
        'doublestruck': ['𝕒', '𝕓', '𝕔', '𝕕', '𝕖', '𝕗', '𝕘', '𝕙', '𝕚', '𝕛', '𝕜', '𝕝', '𝕞', '𝕟', '𝕠', '𝕡', '𝕢', '𝕣', '𝕤', '𝕥', '𝕦', '𝕧', '𝕨', '𝕩', '𝕪', '𝕫', '𝔸', '𝔹', 'ℂ',
                         '𝔻', '𝔼', '𝔽', '𝔾', 'ℍ', '𝕀', '𝕁', '𝕂', '𝕃', '𝕄', 'ℕ', '𝕆', 'ℙ', 'ℚ', 'ℝ', '𝕊', '𝕋', '𝕌', '𝕍', '𝕎', '𝕏', '𝕐', 'ℤ', '𝟘', '𝟙', '𝟚', '𝟛', '𝟜', '𝟝', '𝟞',
                         '𝟟', '𝟠', '𝟡', '❕', '❔', '.', ',', '"', "'"],
        'capitalized': ['ᴀ', 'ʙ', 'ᴄ', 'ᴅ', 'ᴇ', 'ꜰ', 'ɢ', 'ʜ', 'ɪ', 'ᴊ', 'ᴋ', 'ʟ', 'ᴍ', 'ɴ', 'ᴏ', 'ᴘ', 'q', 'ʀ', 'ꜱ', 'ᴛ', 'ᴜ', 'ᴠ', 'ᴡ', 'x', 'ʏ', 'ᴢ', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I',
                        'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '﹗', '﹖', '﹒', '﹐', '"', "'"],
        'circled': ['ⓐ', 'ⓑ', 'ⓒ', 'ⓓ', 'ⓔ', 'ⓕ', 'ⓖ', 'ⓗ', 'ⓘ', 'ⓙ', 'ⓚ', 'ⓛ', 'ⓜ', 'ⓝ', 'ⓞ', 'ⓟ', 'ⓠ', 'ⓡ', 'ⓢ', 'ⓣ', 'ⓤ', 'ⓥ', 'ⓦ', 'ⓧ', 'ⓨ', 'ⓩ', 'Ⓐ', 'Ⓑ', 'Ⓒ', 'Ⓓ', 'Ⓔ', 'Ⓕ', 'Ⓖ', 'Ⓗ', 'Ⓘ', 'Ⓙ',
                    'Ⓚ', 'Ⓛ', 'Ⓜ', 'Ⓝ', 'Ⓞ', 'Ⓟ', 'Ⓠ', 'Ⓡ', 'Ⓢ', 'Ⓣ', 'Ⓤ', 'Ⓥ', 'Ⓦ', 'Ⓧ', 'Ⓨ', 'Ⓩ', '⓪', '①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨', '!', '?', '.', ',', '"', "'"],
        'parenthesized': ['⒜', '⒝', '⒞', '⒟', '⒠', '⒡', '⒢', '⒣', '⒤', '⒥', '⒦', '⒧', '⒨', '⒩', '⒪', '⒫', '⒬', '⒭', '⒮', '⒯', '⒰', '⒱', '⒲', '⒳', '⒴', '⒵', '🄐', '🄑', '🄒', '🄓', '🄔', '🄕', '🄖',
                          '🄗', '🄘', '🄙', '🄚', '🄛', '🄜', '🄝', '🄞', '🄟', '🄠', '🄡', '🄢', '🄣', '🄤', '🄥', '🄦', '🄧', '🄨', '🄩', '⓿', '⑴', '⑵', '⑶', '⑷', '⑸', '⑹', '⑺', '⑻', '⑼', '!', '?',
                          '.', ',', '"', "'"],
    }

    #TODO: use warning sign and check for more general insights, while for the individual values you can use traffic light emojis (green, orange, red etc...)
    emoji_table = {
        'bad_news': ['⚠'],
        'good_news': ['✅'],
        'empty_circle': ['⚪'],
        'green_circle': ['🟢'],
        'cancel_button': ['❌'],
        'arrow': ['➤'],
        'small_arrow': ['->'],
        'energy': ['🔥'],
        'protein': ['🍖'],
        'sugar': ['🍬'],
        'fat': ['🧈'],
        'carbohydrates': ['🍝'],
        'sodium': ['🧂'],
        'arrow_up': ['⬆'],
        'arrow_down': ['⬇'],
        'arrow_balance': ['↔'],
        'hand_up' : ['👆'],
        'hand_ok': ['👌'],
        'hand_down': ['👇'],
        'hand_victory': ['✌'],
        'hand_stop': ['✋'],
        'happy' : ['😊','☺️','🙂','😄','😁','😃','😎'],
        'embarassed' : ['😳'],
        'sad' : ['😕'],
        'confused' : ['🤔','🤨','🧐'],
        'wondering' : ['🤔'],
        'sorry': ['😔'],
        'ashamed': ['😅'],
        'sarcastic' : ['🙃'],
        'chart' : ['📈'],
        'magnifier': ['🔎'],
        'test1': ['😞'],
        'test2': ['😕'],
        'test3': ['😐'],
        'test4': ['🙂'],
        'polite_smile': ['😊'],
        'persevere': ['🙏'],
    }

    whitespaces = {
        'newline' : '\n',
        'space' : ' '
    }

    thresholds_values = [0,5,10,15,25,50,75,90,100,110,125,150,175,200,300,400]
    almost_ideal_thresholds = [90,100,110]

    communicator = Communicator()

    # TODO: move to appropriate structure
    thresholds = {
        'val': {
            tuple([0],): ['none'],
            tuple([5]): ['almost no'],
            tuple([10,15]): ['just a bit'],
            tuple([25,125]): ['a quarter'],
            tuple([50, 150]): ['half'],
            tuple([75,175]): ['three quarters'],
            tuple([90]): ['almost the right amount'],
            tuple([100]): ['the right amount'],
            tuple([110]): ['a bit'],
            tuple([200]): ['x2'],
            tuple([300]): ['x3'],
            tuple([400]): ['x4'],
        },
        'dist': {
            tuple([0,]): ['none'],
            tuple([5,10,15]): ['just a bit'],
            tuple([25]): ['a quarter'],
            tuple([50]): ['half'],
            tuple([75]): ['three quarters'],
            tuple([90]): ['almost your whole requirement','almost twice '],
            tuple([100]): ['your whole requirement','twice'],
            tuple([200]): ['x2'],
            tuple([300]): ['x3'],
            tuple([400]): ['x4'],
        },
        'compact': {
            tuple([0], ): ['none'],
            tuple([5]): ['almost none'],
            tuple([10, 15]): ['a bit'],
            tuple([25]): ['a quarter'],
            tuple([50]): ['halfway through'],
            tuple([75]): ['a quarter left'],
            tuple([90]): ['almost ok'],
            tuple([100]): ['ok!'],
            tuple([110]): ['a bit too much'],
            tuple([125]): ['a quarter too much'],
            tuple([150]): ['halfway over'],
            tuple([175]): ['three quarters too much'],
            tuple([200]): ['x2 too much'],
            tuple([300]): ['x3 too much'],
            tuple([400]): ['x4 too much'],
        }
    }

    postfixes = {
        'val': {
            tuple([0, 5, 10, 15]): ['of it'],
            tuple([25, 50, 75]): [],
            tuple([90]): [],
            tuple([100]): [],
            tuple([110]): ['too much'],
            tuple([125, 150, 175, 200, 300, 400]): ['excess'],
        },
        'dist': {
            tuple([0],): ['deficit or excess'],
            tuple([5,10,15]): ['deficit','excess'],
            tuple([25,50,75]): ['missing','excess'],
            tuple([100]): ['is missing', 'in excess'],
            tuple([90,200,300,400]): ['is missing', 'more'],
        }
    }

    postfixes_goal = {
        'val': {
            tuple([0,5,10,15]): ['of your requirements'],
            tuple([25, 50, 75]): ['of your goal'],
            tuple([90]): [],
            tuple([100]): [],
            tuple([110,125, 150, 175, 200, 300, 400]): ['more than your goal']
        },
        'dist': {
            tuple([0]): ['deficit or excess'],
            tuple([5,10,15,25,50,75,]): ['less than your goal','more than your goal'],
            tuple([90,100]): ['less than your goal','more than your goal'],
            tuple([200,300,400]): ['more than your goal'],
        }
    }

    tag_setups = {
        'val_compact': {'thresholds_key': 'compact'},
        'val_pf_g': {'thresholds_key': 'val', 'postfix': True, 'compare_to_goal': True},
        'val_pf': {'thresholds_key': 'val', 'postfix': True},
        'val_dist_pf_g': {'thresholds_key': 'val', 'compare_to_dist': True, 'compare_to_goal': True, 'postfix': True},
        'val_dist': {'thresholds_key': 'val', 'compare_to_dist': True, 'postfix': True},
        'val': {'thresholds_key': 'val'},
        'dist_pf_g': {'thresholds_key': 'dist', 'postfix': True, 'compare_to_goal': True},
        'dist_pf': {'thresholds_key': 'dist', 'postfix': True},
        'dist': {'thresholds_key': 'dist'}
    }


    tolerance = 3

    polarities = {'+': 'more than', '-': 'less than'}

    def format_str(self, val):
        return int(val.replace('%',''))

    def is_almost_ok(self,val, aliases):
        if val > self.almost_ideal_thresholds[-1] or val < self.almost_ideal_thresholds[0]:
            return False
        distances = {}
        for t in self.thresholds_values:
            distances.update({t: abs(val-t)})
        min_dist = min(distances.values())
        matched = list(distances.keys())[list(distances.values()).index(min_dist)]
        return True if matched in self.almost_ideal_thresholds else False

    #since some thresholds are represented as lists (the meaning change depending on whether the value is bigger or lower than 100)
    def extract_alias(self, val, aliases, compute_dist = False):
        # print('| | aliases:', aliases)
        #if we have to quantify a distance we need the right aliases, but still we have to keep the original value to assess whether it is an excess or a deficit
        # print('| | | extracting alias')
        processed = abs(100-val) if compute_dist else val
        if aliases == []:
            return processed

        if processed > self.thresholds_values[-1]:
            # print(f'| | | greater than top threshold value: {processed} ({type(processed)}) > {self.thresholds_values[-1]} ({type(self.thresholds_values[-1])})')
            key = self.thresholds_values[-1]
            for k in aliases.keys():
                # print('| | | k:', k, f'({type(k)})')
                    # print(f'| | | | {num} ({type(num)})')
                if key in k:
                    # for num in k:
                    # print('| | | key in k')
                    # print('| | | polarity:', self.polarities["+"])
                    # print('| | | aliases[k]:', aliases[k])
                    if len(aliases[k]) > 1:
                        return aliases[k][1]
                    elif len(aliases[k]) > 0:
                        return aliases[k][0]
                    else:
                        return ''
                    # return f'{self.polarities["+"]} '+ aliases[k]

        distances = {}
        for t in self.thresholds_values:
            distances.update({t: abs(processed-t)})
        min_dist = min(distances.values())
        matched = list(distances.keys())[list(distances.values()).index(min_dist)]

        for k,v in aliases.items():
            if matched in k:
                if len(v) > 1:
                    return v[0] if val <= 100 else v[1]
                elif len(v) > 0:
                    return v[0]
                else:
                    return ''

        #case in which the matched threshold was present in the general list but not in the aliases
        #example: 110 is a known threshold but not for distances
        flat_thresholds = set(itertools.chain(*aliases.keys()))  # flattening list
        closest = min(flat_thresholds, key=lambda x:abs(x-matched))
        for k, v in aliases.items():
            if closest in k:
                if len(v) > 1:
                    return v[0] if val <= 100 else v[1]
                elif len(v) > 0:
                    return v[0]
                else:
                    return ''


    #expresses distance (keeping number)
    def distance(self, val, postfix=False):
        paraphrase = ''
        if type(val) == str:
            val = self.format_str(val)
        dist = abs(100-val)
        paraphrase += f'{dist}%'
        if postfix:
            postfix = 'over' if val > 100 else 'below'
            paraphrase += f' {postfix}'

        return paraphrase

    #just returns value
    def value(self, val):
        return val

    #TODO: move to another class?
    #expresses value via means of paraphrases
    def quantify(self, val, thresholds_key = False, postfix=False, compare_to_goal=False, keep_numbers = False, compare_to_dist = False):
        #print(f'#############\nGot {val}\n\tthresholds_key = {thresholds_key}\n\tpostfix={postfix}\n\tcompare_to_goal={compare_to_goal}\n\tkeep_numbers={keep_numbers}\n\tcompare_to_dist={compare_to_dist}')
        if not thresholds_key:
            return 'please provide a valid thresholds list'
        if thresholds_key == 'compact' and (postfix or compare_to_goal or compare_to_dist):
            return 'compact quantification is not meant to provide postixes or comparisons'

        thresholds = self.thresholds[thresholds_key]
        postfixes = [] if thresholds_key=='compact' else (self.postfixes_goal[thresholds_key] if compare_to_goal else self.postfixes[thresholds_key])

        if type(val) == str:
            val = self.format_str(val)

        dist = abs(100-val)

        if compare_to_dist:
            aux_t_alias = self.thresholds['dist']
            # print('| | aux_t_alias (thresholds):', aux_t_alias)
            aux_p_alias = self.postfixes_goal['dist'] if compare_to_goal else self.postfixes['dist']
            # print('| | aux_p_alias (postfix):', aux_p_alias)
            
            aux_t_alias = f'{dist}%' if keep_numbers else self.extract_alias(val, compute_dist=True, aliases=aux_t_alias)
            # print('| | aux_t_alias (alias extracted):', aux_t_alias)
            aux_p_alias = self.extract_alias(val, compute_dist=True, aliases=aux_p_alias) if postfix else ''
            # print('| | aux_p_alias (alias extracted):', aux_p_alias)

        t_alias = (f'{dist}%' if thresholds_key == 'dist' else f'{val}%') if keep_numbers else self.extract_alias(val,thresholds, compute_dist = (True if thresholds_key == 'dist' else False))
        # print('| | t_alias:', t_alias)
        p_alias = self.extract_alias(val, postfixes, compute_dist = (True if thresholds_key == 'dist' else False)) if postfix else ''
        # print('| | p_alias:', p_alias)

        paraphrase = f'{t_alias}'+(f' {p_alias}' if postfix else '') + (f' ({aux_t_alias} {aux_p_alias if postfix else ""})' if compare_to_dist else '')
        # print('| | paraphrase:', paraphrase)

        return paraphrase

    def handle_whitespaces(self, line):
        if len(line.split()) > 0 and line != "":
            #line = ' '.join(filter(None, line.split(' ')))
            line = line.strip().replace('\n', '')\
                               .replace('\t', '')\
                               .replace('#tab#', '    ')\
                               .replace('#newline#', '\n')\
                               .replace('#del#', '')\
                               .replace('#space#',' ')
            return line
        else:
            return False


    def emojification(self, line):
        for code in self.emoji_table.keys():
            emoji = self.communicator.smart_random(self.emoji_table[code])#self.emoji_table[code][random.randint(0,len(self.emoji_table[code])-1)]
            line = line.replace(str('@'+code+'@'), emoji)

        return line

    def get_emoji(self, emoji):
        emoji = emoji.strip()
        try:
            return self.communicator.smart_random(self.emoji_table[emoji])#self.emoji_table[emoji][random.randint(0,len(self.emoji_table[emoji])-1)]
        except:
            return 'EMOJI_NOT_FOUND'

    def quantification(self, line, keep_numbers=False):
        # print('| quantification')
        for tag,args in self.tag_setups.items(): #order is important
            matches = re.findall(r'@'+tag+'(.*?)@',line) if line else False
            if matches:
                # print(f'tag: {tag} | args: {args}')
                # print('matches:', matches)
                for match in matches:
                    # print('| match:', match)
                    replaced_str = self.quantify(match,**args, keep_numbers=keep_numbers)
                    # print('| match quantified')
                    line = re.sub(r'@'+tag+'(.*?)'+match+'(.*?)@', replaced_str, line)

        return line if type(line) is bool else line.replace("  ",' ').replace(') ',')').replace(' )',')')

    def format(self, line):
        for code in [code for code in self.char_format_table.keys() if code!='target']:
            matches = re.findall(r'<'+code+'(.*?)>',line)
            if matches:
                for match in matches:
                    replaced_str = ''
                    for char in match:
                        try:
                            index = self.char_format_table['target'].index(char)
                            replaced_str += self.char_format_table[code][index]
                        except ValueError:
                            replaced_str += char
                    replaced_str.strip()
                    line = re.sub(r'<' + 'val' + '(.*?)>', replaced_str, line)

        return line

if __name__ == '__main__':
    tf = TextFormatterUtility()

    for val in range(0,401):
        print(f'CURRENT VALUE: {val}')
        for el in tf.tag_setups.keys():
            line = f'@{el} {val} @'
            print(f'{el} -> {tf.quantification(line, keep_numbers=False)}')
        print('______________________________________________________')

    #tag_setups = {
    #    'val_compact': {'thresholds_key': 'compact'},
    #    'val_pf_g': {'thresholds_key': 'val', 'postfix': True, 'compare_to_goal': True},
    #    'val_pf': {'thresholds_key': 'val', 'postfix': True},
    #    'val_dist': {'thresholds_key': 'val', 'compare_to_dist': True, 'postfix': True},
    #    'val': {'thresholds_key': 'val'},
    #    'dist_pf_g': {'thresholds_key': 'dist', 'postfix': True, 'compare_to_goal': True},
        #    'dist_pf': {'thresholds_key': 'dist', 'postfix': True},
        #    'dist': {'thresholds_key': 'dist'}
    #}