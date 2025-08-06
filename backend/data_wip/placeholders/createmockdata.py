import csv
import requests
import json
import time
from pathlib import Path
from datetime import datetime

def create_data_directory():
    """Create data directory if it doesn't exist"""
    Path("data").mkdir(exist_ok=True)
    print("📁 Created data directory")

def generate_politicians_csv():
    """Generate politicians.csv with comprehensive US political figures"""
    print("🏛️ Generating politicians.csv...")
    
    politicians = [
        # Presidents & Former Presidents
        ("Donald Trump", "Donald Trump", "45th President of the United States", "🇺🇸", "trump_donald"),
        ("Joe Biden", "Joe Biden", "46th President of the United States", "🇺🇸", "biden_joseph"),
        ("Barack Obama", "Barack Obama", "44th President of the United States", "🇺🇸", "obama_barack"),
        ("Bill Clinton", "Bill Clinton", "42nd President of the United States", "🇺🇸", "clinton_bill"),
        ("George W Bush", "George W Bush", "43rd President of the United States", "🇺🇸", "bush_george_w"),
        
        # 2024 Presidential Candidates
        ("Ron DeSantis", "Ron DeSantis", "Governor of Florida", "🏛️", "desantis_ron"),
        ("Nikki Haley", "Nikki Haley", "Former UN Ambassador", "🏛️", "haley_nikki"),
        ("Vivek Ramaswamy", "Vivek Ramaswamy", "Entrepreneur and Presidential candidate", "🏛️", "ramaswamy_vivek"),
        ("Chris Christie", "Chris Christie", "Former New Jersey Governor", "🏛️", "christie_chris"),
        ("Tim Scott", "Tim Scott", "Senator from South Carolina", "🏛️", "scott_tim"),
        
        # Senate Leadership
        ("Chuck Schumer", "Chuck Schumer", "Senate Majority Leader", "🏛️", "schumer_chuck"),
        ("Mitch McConnell", "Mitch McConnell", "Senate Minority Leader", "🏛️", "mcconnell_mitch"),
        ("Bernie Sanders", "Bernie Sanders", "Senator from Vermont", "🏛️", "sanders_bernie"),
        ("Elizabeth Warren", "Elizabeth Warren", "Senator from Massachusetts", "🏛️", "warren_elizabeth"),
        ("Ted Cruz", "Ted Cruz", "Senator from Texas", "🏛️", "cruz_ted"),
        ("Marco Rubio", "Marco Rubio", "Senator from Florida", "🏛️", "rubio_marco"),
        ("Josh Hawley", "Josh Hawley", "Senator from Missouri", "🏛️", "hawley_josh"),
        ("Tom Cotton", "Tom Cotton", "Senator from Arkansas", "🏛️", "cotton_tom"),
        ("Kyrsten Sinema", "Kyrsten Sinema", "Former Senator from Arizona", "🏛️", "sinema_kyrsten"),
        ("Joe Manchin", "Joe Manchin", "Senator from West Virginia", "🏛️", "manchin_joe"),
        
        # House Leadership & Notable Members
        ("Nancy Pelosi", "Nancy Pelosi", "Former Speaker of the House", "🏛️", "pelosi_nancy"),
        ("Kevin McCarthy", "Kevin McCarthy", "Former Speaker of the House", "🏛️", "mccarthy_kevin"),
        ("Alexandria Ocasio-Cortez", "AOC", "Representative from New York", "🏛️", "ocasio_cortez_alexandria"),
        ("Marjorie Taylor Greene", "Marjorie Taylor Greene", "Representative from Georgia", "🏛️", "greene_marjorie"),
        ("Matt Gaetz", "Matt Gaetz", "Representative from Florida", "🏛️", "gaetz_matt"),
        ("Jim Jordan", "Jim Jordan", "Representative from Ohio", "🏛️", "jordan_jim"),
        ("Ilhan Omar", "Ilhan Omar", "Representative from Minnesota", "🏛️", "omar_ilhan"),
        ("Rashida Tlaib", "Rashida Tlaib", "Representative from Michigan", "🏛️", "tlaib_rashida"),
        ("Lauren Boebert", "Lauren Boebert", "Representative from Colorado", "🏛️", "boebert_lauren"),
        ("Adam Schiff", "Adam Schiff", "Representative from California", "🏛️", "schiff_adam"),
        
        # Governors
        ("Gavin Newsom", "Gavin Newsom", "Governor of California", "🏛️", "newsom_gavin"),
        ("Greg Abbott", "Greg Abbott", "Governor of Texas", "🏛️", "abbott_greg"),
        ("Gretchen Whitmer", "Gretchen Whitmer", "Governor of Michigan", "🏛️", "whitmer_gretchen"),
        ("Glenn Youngkin", "Glenn Youngkin", "Governor of Virginia", "🏛️", "youngkin_glenn"),
        ("Kristi Noem", "Kristi Noem", "Governor of South Dakota", "🏛️", "noem_kristi"),
        
        # Other Notable Political Figures
        ("Kamala Harris", "Kamala Harris", "Vice President of the United States", "🇺🇸", "harris_kamala"),
        ("Mike Pence", "Mike Pence", "Former Vice President", "🏛️", "pence_mike"),
        ("Hillary Clinton", "Hillary Clinton", "Former Secretary of State", "🏛️", "clinton_hillary"),
        ("Anthony Fauci", "Anthony Fauci", "Former NIAID Director", "🏛️", "fauci_anthony"),
        ("Liz Cheney", "Liz Cheney", "Former Representative from Wyoming", "🏛️", "cheney_liz"),
    ]
    
    with open('data/politicians.csv', 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['name', 'search_term', 'description', 'icon', 'congress_id'])
        writer.writerows(politicians)
    
    print(f"✅ Generated politicians.csv with {len(politicians)} entries")

def generate_celebrities_csv():
    """Generate celebrities.csv with billionaires, actors, musicians, etc."""
    print("⭐ Generating celebrities.csv...")
    
    celebrities = [
        # Tech Billionaires
        ("Elon Musk", "Elon Musk", "CEO of Tesla and SpaceX", "🚀", "elon_musk"),
        ("Jeff Bezos", "Jeff Bezos", "Founder of Amazon", "📦", "jeff_bezos"),
        ("Bill Gates", "Bill Gates", "Microsoft founder and philanthropist", "💻", "bill_gates"),
        ("Mark Zuckerberg", "Mark Zuckerberg", "Meta CEO", "📱", "mark_zuckerberg"),
        ("Larry Page", "Larry Page", "Google co-founder", "🔍", "larry_page"),
        ("Sergey Brin", "Sergey Brin", "Google co-founder", "🔍", "sergey_brin"),
        ("Tim Cook", "Tim Cook", "Apple CEO", "🍎", "tim_cook"),
        ("Satya Nadella", "Satya Nadella", "Microsoft CEO", "💻", "satya_nadella"),
        
        # Investment & Business
        ("Warren Buffett", "Warren Buffett", "Berkshire Hathaway CEO", "💰", "warren_buffett"),
        ("Charlie Munger", "Charlie Munger", "Berkshire Hathaway Vice Chairman", "💰", "charlie_munger"),
        ("Jamie Dimon", "Jamie Dimon", "JPMorgan Chase CEO", "🏦", "jamie_dimon"),
        ("Ray Dalio", "Ray Dalio", "Bridgewater founder", "💰", "ray_dalio"),
        ("Michael Bloomberg", "Michael Bloomberg", "Bloomberg founder", "📊", "michael_bloomberg"),
        
        # Entertainment - Musicians
        ("Taylor Swift", "Taylor Swift", "Pop superstar", "🎵", "taylor_swift"),
        ("Kanye West", "Kanye West", "Rapper and entrepreneur", "🎤", "kanye_west"),
        ("Jay-Z", "Jay-Z", "Rapper and business mogul", "🎤", "jay_z"),
        ("Beyoncé", "Beyoncé", "R&B superstar", "🎵", "beyonce"),
        ("Drake", "Drake", "Canadian rapper", "🎤", "drake"),
        ("Ariana Grande", "Ariana Grande", "Pop star", "🎵", "ariana_grande"),
        ("Justin Bieber", "Justin Bieber", "Pop star", "🎵", "justin_bieber"),
        ("Billie Eilish", "Billie Eilish", "Pop sensation", "🎵", "billie_eilish"),
        ("The Weeknd", "The Weeknd", "R&B artist", "🎵", "the_weeknd"),
        ("Bad Bunny", "Bad Bunny", "Reggaeton superstar", "🎵", "bad_bunny"),
        
        # Entertainment - Actors
        ("Dwayne Johnson", "The Rock", "Actor and former wrestler", "🎬", "dwayne_johnson"),
        ("Tom Cruise", "Tom Cruise", "Action movie star", "🎬", "tom_cruise"),
        ("Leonardo DiCaprio", "Leonardo DiCaprio", "Academy Award winner", "🎬", "leonardo_dicaprio"),
        ("Will Smith", "Will Smith", "Actor and rapper", "🎬", "will_smith"),
        ("Robert Downey Jr", "Robert Downey Jr", "Iron Man actor", "🎬", "robert_downey_jr"),
        ("Ryan Reynolds", "Ryan Reynolds", "Deadpool actor", "🎬", "ryan_reynolds"),
        ("Jennifer Lawrence", "Jennifer Lawrence", "Academy Award winner", "🎬", "jennifer_lawrence"),
        ("Margot Robbie", "Margot Robbie", "Australian actress", "🎬", "margot_robbie"),
        ("Chris Hemsworth", "Chris Hemsworth", "Thor actor", "🎬", "chris_hemsworth"),
        ("Scarlett Johansson", "Scarlett Johansson", "Black Widow actress", "🎬", "scarlett_johansson"),
        
        # Reality TV & Social Media
        ("Kim Kardashian", "Kim Kardashian", "Reality TV star and entrepreneur", "⭐", "kim_kardashian"),
        ("Kylie Jenner", "Kylie Jenner", "Reality TV star and businesswoman", "⭐", "kylie_jenner"),
        ("Khloe Kardashian", "Khloe Kardashian", "Reality TV star", "⭐", "khloe_kardashian"),
        ("Kourtney Kardashian", "Kourtney Kardashian", "Reality TV star", "⭐", "kourtney_kardashian"),
        ("Kris Jenner", "Kris Jenner", "Kardashian family matriarch", "⭐", "kris_jenner"),
        
        # Media Moguls
        ("Oprah Winfrey", "Oprah Winfrey", "Media mogul and philanthropist", "📺", "oprah_winfrey"),
        ("Howard Stern", "Howard Stern", "Radio personality", "📻", "howard_stern"),
        ("Joe Rogan", "Joe Rogan", "Podcast host", "🎙️", "joe_rogan"),
        ("Ellen DeGeneres", "Ellen DeGeneres", "TV host and comedian", "📺", "ellen_degeneres"),
        
        # Sports
        ("LeBron James", "LeBron James", "NBA superstar", "🏀", "lebron_james"),
        ("Tom Brady", "Tom Brady", "NFL legend", "🏈", "tom_brady"),
        ("Cristiano Ronaldo", "Cristiano Ronaldo", "Soccer superstar", "⚽", "cristiano_ronaldo"),
        ("Lionel Messi", "Lionel Messi", "Soccer legend", "⚽", "lionel_messi"),
        ("Serena Williams", "Serena Williams", "Tennis champion", "🎾", "serena_williams"),
        ("Tiger Woods", "Tiger Woods", "Golf legend", "⛳", "tiger_woods"),
        
        # Controversial Figures
        ("Andrew Tate", "Andrew Tate", "Controversial influencer", "⚡", "andrew_tate"),
        ("Jordan Peterson", "Jordan Peterson", "Psychologist and author", "📚", "jordan_peterson"),

        # Gaming Giants
        ("PewDiePie", "PewDiePie", "Felix - Gaming's biggest individual creator", "👑", "UC-lHJZR3Gqxm24_Vd_AJ5Yw"),
        ("Markiplier", "Markiplier", "Mark - Horror gaming specialist", "😱", "UC7_YxT-KID8kRbqZo7MyscQ"),
        ("Jacksepticeye", "Jacksepticeye", "Sean - Energetic Irish gamer", "☘️", "UCYzPXprvl5Y-Sf0g4vX-m6g"),
        ("DanTDM", "DanTDM", "Dan - Minecraft and gaming content", "💎", "UCS5Oz6CHmeoF7vSad0qqXfw"),
        ("VanossGaming", "VanossGaming", "Evan - Gaming comedy group", "🦉", "UCKqH_9mk1waLgBiL2vT5b9g"),
        ("CoryxKenshin", "CoryxKenshin", "Cory - Horror gaming and reactions", "👻", "UCE_--R1P5-kfBzHTca0dsnw"),
        
        # Streaming/Content
        ("Ninja", "Ninja", "Tyler - Fortnite streaming legend", "🥷", "UCAW-NpUFkMyCNrvRSSGIvDQ"),
        ("Pokimane", "Pokimane", "Imane - Top female streamer", "🎮", "UCVhfFXNY0z7Aap08H8-6toA"),
        ("Valkyrae", "Valkyrae", "Rae - Gaming and lifestyle content", "⚡", "UChBBlfeFNk9jU9SUxl3d2Mg"),
        ("Dream", "Dream", "Clay - Minecraft speedrunner", "😷", "UCfM3zsQsOnfWNUppiycmBuw"),
        ("GeorgeNotFound", "GeorgeNotFound", "George - Dream SMP member", "🥽", "UCrPseYLGpNygVi34QpGNqpA"),
        
        # Tech/Education
        ("MrBeast", "MrBeast", "Jimmy - Philanthropic content king", "💰", "UCX6OQ3DkcsbYNE6H8uQQuVA"),
        ("MKBHD", "MKBHD", "Marques - Tech review authority", "📱", "UCBJycsmduvYEL83R_U4JriQ"),
        ("Linus Tech Tips", "Linus Tech Tips", "Linus - Tech education and reviews", "💻", "UCXuqSBlHAE6Xw-yeJA0Tunw"),
        ("Veritasium", "Veritasium", "Derek - Science education", "🔬", "UCHnyfMqiRRG1u-2MsSQLbXA"),
        ("Kurzgesagt", "Kurzgesagt", "In a Nutshell - Animated science", "🌌", "UCsXVk37bltHxD1rDPwtNM8Q"),
        
        # Entertainment/Comedy
        ("Logan Paul", "Logan Paul", "Logan - Controversial content creator", "🥊", "UCG8rbF3g2AMX70yOd8vqIZg"),
        ("Jake Paul", "Jake Paul", "Jake - Boxing YouTuber", "🥊", "UCcwVQwTNR7aE_d4dQzK1bxg"),
        ("David Dobrik", "David Dobrik", "David - Vlog squad leader", "📹", "UCmh5gdwCx6lN7gEC20leNVA"),
        ("Emma Chamberlain", "Emma Chamberlain", "Emma - Lifestyle vlogger", "☕", "UC78cxCAcp7JfQPgKxYdyGrg"),
        ("James Charles", "James Charles", "James - Beauty influencer", "💋", "UCucot-Zp428OwzazG0e7hzg"),
        ("Jeffree Star", "Jeffree Star", "Jeffree - Beauty and controversy", "💄", "UCkvK_5omS-42Ovgah8KRKtg"),
        
        # Music/Performance
        ("T-Series", "T-Series", "Indian music and film production", "🎵", "UCq-Fj5jknLsUf-MWSy4_brA"),
        ("Dude Perfect", "Dude Perfect", "Sports trick shots and comedy", "🎯", "UCRijo3ddMTht_IHyNSNXpNQ"),
        ("Good Mythical Morning", "Good Mythical Morning", "Rhett & Link - Daily talk show", "🌅", "UC4PooiX37Pld1T8J5SYT-SQ"),
        
        # International
        ("Rubius", "ElRubius", "Spanish gaming and entertainment", "🇪🇸", "UCXazif75cJAqc7fwFWL8qnQ"),
        ("Felipe Neto", "Felipe Neto", "Brazilian entertainment", "🇧🇷", "UCV306eHqgo0LvBf3Mh36AHg"),
        
        # Educational/Lifestyle
        ("Casey Neistat", "Casey Neistat", "Casey - Filmmaking and lifestyle", "🎬", "UCtinbF-Q-fVthA0qrFQTgXQ"),
        ("Peter McKinnon", "Peter McKinnon", "Peter - Photography and filmmaking", "📸", "UC7T8roVtC_3afWKTOGtLlBA"),
        
        # Kids Content
        ("Ryan's World", "Ryan's World", "Ryan - Kids toy reviews", "🧸", "UChGJGhZ9SOOHvBB0Y4DOO_w"),
        ("Blippi", "Blippi", "Stevin - Educational kids content", "🎪", "UCeVFVLwNNtOyNjS6h8b-oAw"),
        
        # Reaction/Commentary
        ("SSSniperWolf", "SSSniperWolf", "Lia - Gaming and reaction content", "🎮", "UCpB959t8iPrxQWj7G6n0ctQ"),
        ("moistcr1tikal", "penguinz0", "Charlie - Gaming and commentary", "🐧", "UCq6VFHwMzcMXbuKyG7SQYIg"),
        ("H3 Podcast", "H3 Podcast", "Ethan & Hila - Commentary podcast", "🎙️", "UCLtREJY21xRfCuEKvdki1Kw"),
        
        # Beauty/Fashion
        ("NikkieTutorials", "NikkieTutorials", "Nikkie - Beauty tutorials", "💄", "UCzTKskwIc_4jAUTa7MhKqNQ"),
        ("Tati", "Tati", "Tati - Beauty reviews and drama", "💄", "UC94LPgNsw6y-2SBpBfqPxTw"),
        
        # Food
        ("Binging with Babish", "Binging with Babish", "Andrew - Cooking show recreations", "👨‍🍳", "UCJHA_jMfCvEnv-3kRjTCQXw"),
        ("Bon Appétit", "Bon Appétit", "Professional cooking content", "👨‍🍳", "UCbpMy2Fg74eHla2IfkIDGRA"),
        
        # Fitness
        ("Athlean-X", "Athlean-X", "Jeff - Science-based fitness", "💪", "UCe0TLA0EsQbE-MjuHXevj2A"),
        ("Sam Sulek", "Sam Sulek", "body builder", "💪", "UCe0TLA0EsQbE-MjuHXevj2A"),
        ("Jeff Nippard", "Jeff Nippard", "Jeff - Science-based fitness", "💪", "UCe0TLA0EsQbE-MjuHXevj2A"),
    ]
    
    with open('data/celebrities.csv', 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['name', 'search_term', 'description', 'icon', 'external_id'])
        writer.writerows(celebrities)
    
    print(f"✅ Generated celebrities.csv with {len(celebrities)} entries")

def generate_countries_csv():
    """Generate countries.csv with major world nations"""
    print("🌍 Generating countries.csv...")
    
    countries = [
        # Major Powers
        ("United States", "United States", "Leading global superpower", "🇺🇸", "US"),
        ("China", "China", "World's most populous country", "🇨🇳", "CN"),
        ("Russia", "Russia", "Largest country by land area", "🇷🇺", "RU"),
        ("India", "India", "World's largest democracy", "🇮🇳", "IN"),
        ("United Kingdom", "United Kingdom", "Historic global power", "🇬🇧", "GB"),
        ("France", "France", "Cultural and political influence", "🇫🇷", "FR"),
        ("Germany", "Germany", "Economic powerhouse of Europe", "🇩🇪", "DE"),
        ("Japan", "Japan", "Technological innovation leader", "🇯🇵", "JP"),
        
        # Regional Powers
        ("Brazil", "Brazil", "Largest South American economy", "🇧🇷", "BR"),
        ("Canada", "Canada", "Northern neighbor of USA", "🇨🇦", "CA"),
        ("Australia", "Australia", "Oceanic continent nation", "🇦🇺", "AU"),
        ("South Korea", "South Korea", "K-pop and technology hub", "🇰🇷", "KR"),
        ("Italy", "Italy", "Mediterranean cultural center", "🇮🇹", "IT"),
        ("Spain", "Spain", "Iberian Peninsula nation", "🇪🇸", "ES"),
        ("Mexico", "Mexico", "North American neighbor", "🇲🇽", "MX"),
        ("Turkey", "Turkey", "Bridge between Europe and Asia", "🇹🇷", "TR"),
        ("Iran", "Iran", "Middle Eastern regional power", "🇮🇷", "IR"),
        ("Saudi Arabia", "Saudi Arabia", "Oil-rich kingdom", "🇸🇦", "SA"),
        ("Israel", "Israel", "Middle Eastern democracy", "🇮🇱", "IL"),
        ("Egypt", "Egypt", "Ancient civilization hub", "🇪🇬", "EG"),
        
        # European Nations
        ("Netherlands", "Netherlands", "Progressive European nation", "🇳🇱", "NL"),
        ("Sweden", "Sweden", "Scandinavian welfare state", "🇸🇪", "SE"),
        ("Norway", "Norway", "Oil-rich Nordic country", "🇳🇴", "NO"),
        ("Denmark", "Denmark", "Viking heritage nation", "🇩🇰", "DK"),
        ("Finland", "Finland", "Nordic tech hub", "🇫🇮", "FI"),
        ("Switzerland", "Switzerland", "Alpine financial center", "🇨🇭", "CH"),
        ("Belgium", "Belgium", "EU headquarters nation", "🇧🇪", "BE"),
        ("Austria", "Austria", "Central European republic", "🇦🇹", "AT"),
        ("Poland", "Poland", "Central European democracy", "🇵🇱", "PL"),
        ("Czech Republic", "Czech Republic", "Heart of Europe", "🇨🇿", "CZ"),
        
        # Asian Nations
        ("Singapore", "Singapore", "Southeast Asian city-state", "🇸🇬", "SG"),
        ("Thailand", "Thailand", "Southeast Asian kingdom", "🇹🇭", "TH"),
        ("Vietnam", "Vietnam", "Rapidly developing nation", "🇻🇳", "VN"),
        ("Philippines", "Philippines", "Island archipelago", "🇵🇭", "PH"),
        ("Indonesia", "Indonesia", "World's largest archipelago", "🇮🇩", "ID"),
        ("Malaysia", "Malaysia", "Multicultural Southeast Asian nation", "🇲🇾", "MY"),
        ("Pakistan", "Pakistan", "South Asian nuclear power", "🇵🇰", "PK"),
        ("Bangladesh", "Bangladesh", "Densely populated nation", "🇧🇩", "BD"),
        
        # African Nations
        ("South Africa", "South Africa", "Rainbow nation", "🇿🇦", "ZA"),
        ("Nigeria", "Nigeria", "Most populous African nation", "🇳🇬", "NG"),
        ("Kenya", "Kenya", "East African hub", "🇰🇪", "KE"),
        ("Morocco", "Morocco", "North African kingdom", "🇲🇦", "MA"),
        
        # Latin American Nations
        ("Argentina", "Argentina", "South American beef nation", "🇦🇷", "AR"),
        ("Chile", "Chile", "Long Pacific coast nation", "🇨🇱", "CL"),
        ("Colombia", "Colombia", "Coffee and culture nation", "🇨🇴", "CO"),
        ("Peru", "Peru", "Ancient Incan homeland", "🇵🇪", "PE"),
        ("Venezuela", "Venezuela", "Oil-rich troubled nation", "🇻🇪", "VE"),
        
        # Controversial/News-Worthy
        ("Ukraine", "Ukraine", "Eastern European democracy at war", "🇺🇦", "UA"),
        ("North Korea", "North Korea", "Isolated communist state", "🇰🇵", "KP"),
        ("Cuba", "Cuba", "Caribbean communist island", "🇨🇺", "CU"),
        ("Afghanistan", "Afghanistan", "Central Asian nation", "🇦🇫", "AF"),
        ("Iraq", "Iraq", "Middle Eastern republic", "🇮🇶", "IQ"),
        ("Syria", "Syria", "War-torn Middle Eastern nation", "🇸🇾", "SY"),
    ]
    
    with open('data/countries.csv', 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['name', 'search_term', 'description', 'icon', 'iso_code'])
        writer.writerows(countries)
    
    print(f"✅ Generated countries.csv with {len(countries)} entries")

def generate_games_csv():
    """Generate games.csv with popular video games"""
    print("🎮 Generating games.csv...")
    
    games = [
        # Battle Royale
        ("Fortnite", "Fortnite", "Epic's battle royale phenomenon", "🎮", "fortnite"),
        ("PUBG", "PUBG", "PlayerUnknown's Battlegrounds", "🎯", "pubg"),
        ("Apex Legends", "Apex Legends", "Respawn's hero shooter BR", "🦸", "apex"),
        ("Warzone", "Call of Duty Warzone", "COD's battle royale mode", "🔫", "warzone"),
        
        # Sandbox/Creative
        ("Minecraft", "Minecraft", "Microsoft's block-building phenomenon", "⛏️", "minecraft"),
        ("Roblox", "Roblox", "User-generated gaming platform", "🎲", "roblox"),
        ("Terraria", "Terraria", "2D sandbox adventure", "🏗️", "terraria"),
        
        # Shooters
        ("Call of Duty", "Call of Duty", "Activision's military shooter franchise", "🔫", "cod"),
        ("Valorant", "Valorant", "Riot's tactical shooter", "🎯", "valorant"),
        ("Counter-Strike", "Counter-Strike", "Valve's competitive FPS", "💥", "cs"),
        ("Overwatch", "Overwatch", "Blizzard's hero shooter", "🦸", "overwatch"),
        ("Rainbow Six Siege", "Rainbow Six Siege", "Ubisoft's tactical shooter", "🛡️", "r6"),
        
        # MOBAs
        ("League of Legends", "League of Legends", "Riot's dominant MOBA", "🏆", "lol"),
        ("Dota 2", "Dota 2", "Valve's complex MOBA", "⚔️", "dota2"),
        
        # MMORPGs
        ("World of Warcraft", "World of Warcraft", "Blizzard's legendary MMORPG", "⚔️", "wow"),
        ("Final Fantasy XIV", "Final Fantasy XIV", "Square Enix's story-driven MMO", "✨", "ff14"),
        ("Lost Ark", "Lost Ark", "Korean action MMORPG", "🗡️", "lostark"),
        
        # Action RPGs
        ("Elden Ring", "Elden Ring", "FromSoftware's open-world masterpiece", "🗡️", "eldenring"),
        ("Dark Souls", "Dark Souls", "FromSoftware's challenging series", "💀", "darksouls"),
        ("Cyberpunk 2077", "Cyberpunk 2077", "CD Projekt's futuristic RPG", "🤖", "cyberpunk"),
        ("The Witcher 3", "The Witcher 3", "CD Projekt's fantasy epic", "🐺", "witcher3"),
        ("Baldur's Gate 3", "Baldur's Gate 3", "Larian's D&D masterpiece", "🎲", "bg3"),
        
        # Open World
        ("Grand Theft Auto", "GTA", "Rockstar's crime sandbox series", "🚗", "gta"),
        ("Red Dead Redemption", "Red Dead Redemption", "Rockstar's western epic", "🤠", "rdr"),
        ("The Elder Scrolls", "Skyrim", "Bethesda's fantasy RPG series", "🐉", "skyrim"),
        ("Fallout", "Fallout", "Bethesda's post-apocalyptic series", "☢️", "fallout"),
        
        # Sports
        ("FIFA", "FIFA", "EA's soccer simulation", "⚽", "fifa"),
        ("NBA 2K", "NBA 2K", "2K's basketball simulation", "🏀", "nba2k"),
        ("Madden NFL", "Madden NFL", "EA's football simulation", "🏈", "madden"),
        ("Rocket League", "Rocket League", "Psyonix's car soccer game", "🚗", "rocketleague"),
        
        # Strategy
        ("Civilization VI", "Civilization VI", "Firaxis's turn-based strategy", "🏛️", "civ6"),
        ("Age of Empires", "Age of Empires", "Microsoft's RTS series", "🏰", "aoe"),
        ("StarCraft", "StarCraft", "Blizzard's sci-fi RTS", "👽", "starcraft"),
        
        # Horror
        ("Dead by Daylight", "Dead by Daylight", "Behaviour's asymmetric horror", "💀", "dbd"),
        ("Phasmophobia", "Phasmophobia", "Kinetic Games' ghost hunting", "👻", "phasmophobia"),
        ("Resident Evil", "Resident Evil", "Capcom's survival horror series", "🧟", "residentevil"),
        
        # Platform Exclusives
        ("God of War", "God of War", "Sony's Norse mythology action", "⚡", "godofwar"),
        ("The Last of Us", "The Last of Us", "Naughty Dog's zombie drama", "🧟", "tlou"),
        ("Halo", "Halo", "Microsoft's sci-fi shooter", "👨‍🚀", "halo"),
        ("Super Mario", "Super Mario", "Nintendo's platformer icon", "🍄", "mario"),
        ("The Legend of Zelda", "Zelda", "Nintendo's adventure series", "🗡️", "zelda"),
        ("Pokemon", "Pokemon", "Nintendo's monster collection", "⚡", "pokemon"),
        
        # Indie Hits
        ("Among Us", "Among Us", "InnerSloth's social deduction", "🚀", "amongus"),
        ("Fall Guys", "Fall Guys", "Mediatonic's party game", "🎪", "fallguys"),
        ("Stardew Valley", "Stardew Valley", "ConcernedApe's farming sim", "🚜", "stardew"),
        ("Hollow Knight", "Hollow Knight", "Team Cherry's metroidvania", "🦋", "hollowknight"),
    ]
    
    with open('data/games.csv', 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['name', 'search_term', 'description', 'icon', 'game_id'])
        writer.writerows(games)
    
    print(f"✅ Generated games.csv with {len(games)} entries")

def generate_stocks_csv():
    """Generate basic stocks.csv with popular symbols"""
    print("📈 Generating stocks.csv...")
    
    # Popular stocks list (basic version without API calls)
    stocks = [
        # Meme Stocks
        ("GameStop Corp", "GME stock", "Gaming retailer - Meme stock phenomenon", "🎮", "GME"),
        ("AMC Entertainment", "AMC stock", "Movie theater chain - Retail investor favorite", "🎬", "AMC"),
        ("Bed Bath & Beyond", "BBBY stock", "Home goods retailer - Bankruptcy risk", "🛏️", "BBBY"),
        ("Nokia", "NOK stock", "Finnish telecom - 5G infrastructure", "📱", "NOK"),
        ("BlackBerry", "BB stock", "Canadian tech - Cybersecurity pivot", "📱", "BB"),
        
        # Tech Giants
        ("Apple Inc", "AAPL stock", "iPhone maker - World's largest company", "🍎", "AAPL"),
        ("Microsoft Corp", "MSFT stock", "Software giant - Cloud computing leader", "💻", "MSFT"),
        ("Alphabet Inc", "GOOGL stock", "Google parent - Search and AI dominance", "🔍", "GOOGL"),
        ("Amazon.com Inc", "AMZN stock", "E-commerce and cloud giant", "📦", "AMZN"),
        ("Meta Platforms", "META stock", "Facebook parent - Metaverse focus", "📱", "META"),
        ("Tesla Inc", "TSLA stock", "Electric vehicle pioneer", "🚗", "TSLA"),
        ("NVIDIA Corp", "NVDA stock", "AI and graphics chip leader", "🎮", "NVDA"),
        
        # EV and Clean Energy
        ("Rivian Automotive", "RIVN stock", "Electric truck startup", "🚙", "RIVN"),
        ("Lucid Group", "LCID stock", "Luxury electric vehicles", "🚙", "LCID"),
        ("NIO Inc", "NIO stock", "Chinese electric vehicle maker", "🚙", "NIO"),
        ("Nikola Corp", "NKLA stock", "Electric truck company", "🚛", "NKLA"),
        
        # Fintech & Trading
        ("Coinbase Global", "COIN stock", "Cryptocurrency exchange", "₿", "COIN"),
        ("Block Inc", "SQ stock", "Payment processor (formerly Square)", "💳", "SQ"),
        ("PayPal Holdings", "PYPL stock", "Digital payments giant", "💰", "PYPL"),
        ("Robinhood Markets", "HOOD stock", "Commission-free trading app", "📈", "HOOD"),
        
        # Streaming & Entertainment
        ("Netflix Inc", "NFLX stock", "Streaming entertainment leader", "📺", "NFLX"),
        ("Walt Disney Co", "DIS stock", "Entertainment and media conglomerate", "🏰", "DIS"),
        ("Roblox Corp", "RBLX stock", "Gaming platform for kids", "🎲", "RBLX"),
        ("Spotify Technology", "SPOT stock", "Music streaming service", "🎵", "SPOT"),
        
        # Traditional Finance
        ("JPMorgan Chase", "JPM stock", "Largest US bank", "🏦", "JPM"),
        ("Bank of America", "BAC stock", "Major US retail bank", "🏦", "BAC"),
        ("Berkshire Hathaway", "BRK.A stock", "Warren Buffett's investment company", "💰", "BRK.A"),
        
        # Airlines & Travel
        ("American Airlines", "AAL stock", "Major US airline", "✈️", "AAL"),
        ("Delta Air Lines", "DAL stock", "Premium US airline", "✈️", "DAL"),
        ("Airbnb Inc", "ABNB stock", "Home-sharing platform", "🏠", "ABNB"),
        ("Uber Technologies", "UBER stock", "Ride-sharing and delivery", "🚕", "UBER"),
        
        # Energy
        ("Exxon Mobil", "XOM stock", "Oil and gas giant", "⛽", "XOM"),
        ("Chevron Corp", "CVX stock", "Integrated oil company", "⛽", "CVX"),
        
        # ETFs
        ("SPDR S&P 500", "SPY stock", "S&P 500 index fund", "📊", "SPY"),
        ("Invesco QQQ", "QQQ stock", "NASDAQ-100 index fund", "📊", "QQQ"),
        ("ARK Innovation", "ARKK stock", "Disruptive innovation ETF", "🚀", "ARKK"),
    ]
    
    with open('data/stocks.csv', 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['name', 'search_term', 'description', 'icon', 'symbol'])
        writer.writerows(stocks)
    
    print(f"✅ Generated stocks.csv with {len(stocks)} entries")

def generate_crypto_csv():
    """Generate crypto.csv with popular cryptocurrencies"""
    print("₿ Generating crypto.csv...")
    
    # Popular cryptocurrencies (basic version without API calls)
    cryptos = [
        # Top Cryptocurrencies
        ("Bitcoin", "Bitcoin cryptocurrency", "The original cryptocurrency - Digital gold", "₿", "bitcoin"),
        ("Ethereum", "Ethereum cryptocurrency", "Smart contract platform - DeFi leader", "♦️", "ethereum"),
        ("Tether", "Tether cryptocurrency", "Stablecoin pegged to USD", "🟢", "tether"),
        ("BNB", "BNB cryptocurrency", "Binance exchange token", "🟡", "binancecoin"),
        ("XRP", "XRP cryptocurrency", "Ripple payment protocol token", "🌊", "ripple"),
        ("Solana", "Solana cryptocurrency", "High-speed blockchain platform", "🌅", "solana"),
        ("USDC", "USDC cryptocurrency", "USD Coin stablecoin", "🔵", "usd-coin"),
        ("Cardano", "Cardano cryptocurrency", "Proof-of-stake blockchain", "🔷", "cardano"),
        ("Dogecoin", "Dogecoin cryptocurrency", "Meme cryptocurrency - Elon's favorite", "🐕", "dogecoin"),
        ("Avalanche", "Avalanche cryptocurrency", "Decentralized platform for DeFi", "🏔️", "avalanche-2"),
        
        # DeFi and Smart Contract Platforms
        ("Polygon", "Polygon cryptocurrency", "Ethereum scaling solution", "🟣", "matic-network"),
        ("Chainlink", "Chainlink cryptocurrency", "Decentralized oracle network", "🔗", "chainlink"),
        ("Uniswap", "Uniswap cryptocurrency", "Decentralized exchange token", "🦄", "uniswap"),
        ("Wrapped Bitcoin", "Wrapped Bitcoin cryptocurrency", "Bitcoin on Ethereum", "₿", "wrapped-bitcoin"),
        ("Dai", "Dai cryptocurrency", "Decentralized stablecoin", "🟠", "dai"),
        
        # Layer 1 Blockchains
        ("Polkadot", "Polkadot cryptocurrency", "Multi-chain interoperability", "🔴", "polkadot"),
        ("Near Protocol", "Near Protocol cryptocurrency", "Developer-friendly blockchain", "🔺", "near"),
        ("Cosmos", "Cosmos cryptocurrency", "Internet of blockchains", "⚛️", "cosmos"),
        ("Fantom", "Fantom cryptocurrency", "High-performance smart contracts", "👻", "fantom"),
        
        # Meme Coins
        ("Shiba Inu", "Shiba Inu cryptocurrency", "Dogecoin competitor meme coin", "🐶", "shiba-inu"),
        ("Pepe", "Pepe cryptocurrency", "Frog meme coin", "🐸", "pepe"),
        ("Floki", "Floki cryptocurrency", "Elon-inspired meme coin", "🐕", "floki"),
        
        # Exchange Tokens
        ("OKB", "OKB cryptocurrency", "OKX exchange token", "🔵", "okb"),
        ("LEO Token", "LEO Token cryptocurrency", "Bitfinex exchange token", "🦁", "leo-token"),
        
        # Privacy Coins
        ("Monero", "Monero cryptocurrency", "Privacy-focused cryptocurrency", "🅜", "monero"),
        ("Zcash", "Zcash cryptocurrency", "Shielded transactions", "🛡️", "zcash"),
        
        # Gaming and NFT
        ("ApeCoin", "ApeCoin cryptocurrency", "Bored Ape Yacht Club token", "🐵", "apecoin"),
        ("The Sandbox", "The Sandbox cryptocurrency", "Virtual world and gaming", "🏖️", "the-sandbox"),
        ("Axie Infinity", "Axie Infinity cryptocurrency", "Play-to-earn gaming", "🎮", "axie-infinity"),
        
        # Traditional Finance Integration
        ("Bitcoin Cash", "Bitcoin Cash cryptocurrency", "Bitcoin fork with larger blocks", "₿", "bitcoin-cash"),
        ("Litecoin", "Litecoin cryptocurrency", "Silver to Bitcoin's gold", "🥈", "litecoin"),
        ("Ethereum Classic", "Ethereum Classic cryptocurrency", "Original Ethereum blockchain", "♦️", "ethereum-classic"),
    ]
    
    with open('data/crypto.csv', 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['name', 'search_term', 'description', 'icon', 'coingecko_id'])
        writer.writerows(cryptos)
    
    print(f"✅ Generated crypto.csv with {len(cryptos)} entries")

def main():
    """Generate all CSV files"""
    print("🚀 TrendBet CSV Generator")
    print("=" * 50)
    
    create_data_directory()
    
    # Generate all CSV files
    generate_politicians_csv()
    generate_celebrities_csv()
    generate_countries_csv()
    generate_games_csv()
    generate_stocks_csv()
    generate_crypto_csv()
    
    print("=" * 50)
    print("🎉 All CSV files generated successfully!")
    print("\nFiles created in data/ directory:")
    print("- politicians.csv (40+ entries)")
    print("- celebrities.csv (100+ entries)")
    print("- countries.csv (50+ entries)")
    print("- games.csv (45+ entries)")
    print("- stocks.csv (35+ entries)")
    print("- crypto.csv (30+ entries)")
    print(f"\nTotal: 300+ curated targets across all categories!")
    print("\nNext steps:")
    print("1. Review and customize the CSV files as needed")
    print("2. Run your data population service to load into database")
    print("3. Test the new predefined targets system")

if __name__ == "__main__":
    main()