import type { Site } from "@/types";

/**
 * Coordinates are Wikidata points for the structures that have their own entities:
 * Qutb Minar (Q187635), the iron pillar (Q543419), and Alai Darwaza (Q61638119).
 * The mosque has no separate verified point or photograph here.
 * Photographs: IM3847, CC BY-SA 4.0; pawan.kamrani, CC BY-SA 4.0; Alimallick, CC BY-SA 3.0. Wikimedia Commons.
 */
const MINAR_CREDIT = {
  author: "IM3847",
  license: "CC BY-SA 4.0",
  source: "Wikimedia Commons",
} as const;

const PILLAR_CREDIT = {
  author: "pawan.kamrani",
  license: "CC BY-SA 4.0",
  source: "Wikimedia Commons",
} as const;

const DARWAZA_CREDIT = {
  author: "Alimallick",
  license: "CC BY-SA 3.0",
  source: "Wikimedia Commons",
} as const;

export const QUTUB_MINAR: Site = {
  id: "qutub-minar-delhi",
  slug: "qutub-minar",
  name: "Qutub Minar",
  city: "Mehrauli, Delhi",
  country: "India",
  description:
    "A red sandstone minaret in Mehrauli, standing in the Qutb complex beside an earlier mosque.",
  overview:
    "The Qutb Minar was begun under Qutb al-Din Aibak at the end of the 12th century and continued under his successor Iltutmish. Later sultans repaired it, including Firuz Shah Tughlaq after lightning damage. The tower is built of red sandstone and marble. It stands in the Qutb complex next to the Quwwat-ul-Islam mosque. UNESCO inscribed Qutb Minar and its Monuments in 1993.",
  latitude: 28.524355,
  longitude: 77.185248,
  coverImage: "/references/qutb-minar.jpg",
  coverAlt: "Qutub Minar in Mehrauli, Delhi",
  coverCredit: MINAR_CREDIT,
  checkpoints: [
    {
      id: "qutub-minar-tower",
      slug: "minar",
      name: "Qutub Minar",
      category: "tower",
      shortDescription: "The minaret that gives the complex its name.",
      story:
        "The minar is the tall tower of the Qutb complex. Qutb al-Din Aibak began it, and Iltutmish carried the work further. Its balconies mark the stages of the shaft, and the surface is carved sandstone with marble courses. A later repair followed lightning damage. The scanner can compare a photograph with the reference view of the tower.",
      latitude: 28.524355,
      longitude: 77.185248,
      radiusMeters: 30,
      referenceImageUrl: "/references/qutb-minar.jpg",
      referenceImageUrls: ["/references/qutb-minar.jpg"],
      imageCredit: MINAR_CREDIT,
      sortOrder: 1,
    },
    {
      id: "qutub-iron-pillar",
      slug: "iron-pillar",
      name: "Iron pillar",
      category: "pillar",
      shortDescription: "An iron pillar of the Gupta period, standing in the mosque courtyard.",
      story:
        "The iron pillar is about 7 metres high. It carries a Sanskrit inscription of a king named Chandra, usually identified as the Gupta ruler Chandragupta II, and it predates the mosque built around it. It is widely noted for resisting corrosion. The pillar has its own reference photograph, so a clear picture of it can be matched separately from the minar.",
      latitude: 28.524655555556,
      longitude: 77.185069444444,
      radiusMeters: 18,
      referenceImageUrl: "/references/iron-pillar-delhi.jpg",
      referenceImageUrls: ["/references/iron-pillar-delhi.jpg"],
      imageCredit: PILLAR_CREDIT,
      sortOrder: 2,
    },
    {
      id: "qutub-alai-darwaza",
      slug: "alai-darwaza",
      name: "Alai Darwaza",
      category: "gate",
      shortDescription: "The southern gateway added under Alauddin Khalji.",
      story:
        "Alai Darwaza is the gateway Alauddin Khalji added to the mosque in 1311. It is a square building of red sandstone and marble, with a large arch on each side. It has its own reference photograph and a location point, so it can be found on the ground or matched from a picture of the gateway itself.",
      latitude: 28.52425,
      longitude: 77.18572,
      radiusMeters: 20,
      referenceImageUrl: "/references/alai-darwaza.jpg",
      referenceImageUrls: ["/references/alai-darwaza.jpg"],
      imageCredit: DARWAZA_CREDIT,
      sortOrder: 3,
    },
    {
      id: "qutub-quwwat-ul-islam",
      slug: "quwwat-ul-islam",
      name: "Quwwat-ul-Islam mosque",
      category: "mosque",
      shortDescription: "The congregational mosque of the Qutb complex.",
      story:
        "The Quwwat-ul-Islam mosque was begun by Qutb al-Din Aibak and extended under Iltutmish and Alauddin Khalji. Its courtyard is where the iron pillar stands. The prayer screen and colonnades reuse carved stone from earlier temples. A separate coordinate and a reference photograph of the mosque itself are not on record, so this place is read from the guide rather than scanned.",
      sortOrder: 4,
    },
  ],
};
