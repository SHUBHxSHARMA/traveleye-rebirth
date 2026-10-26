import type { Site } from "@/types";

/**
 * The group coordinate is the Wikidata point for Q167298. Its precision is about one minute,
 * so it is not used as a geofence. Kandariya Mahadeva (Q648390) has its own point.
 * Cover photograph: Ms Sarah Welch, “A view from the southside of Kandariya temple 01.jpg”,
 * CC BY-SA 4.0, Wikimedia Commons. It depicts the Kandariya Mahadeva Temple, not the whole group.
 */
const KANDARIYA_CREDIT = {
  author: "Ms Sarah Welch",
  license: "CC BY-SA 4.0",
  source: "Wikimedia Commons",
} as const;

export const KHAJURAHO: Site = {
  id: "khajuraho-group",
  slug: "khajuraho",
  name: "Khajuraho Group of Monuments",
  city: "Khajuraho, Madhya Pradesh",
  country: "India",
  description:
    "A group of Hindu and Jain temples built under the Chandela dynasty in central India.",
  overview:
    "The temples that survive at Khajuraho were built under the Chandela dynasty, mostly from the 10th to the 12th centuries. They follow the north Indian nagara plan, with a porch, a hall, and a tower, and their outer walls carry sculpture of deities, attendants, and couples. The western group is the largest cluster visitors walk through. UNESCO inscribed the Khajuraho Group of Monuments in 1986. Only the Kandariya Mahadeva Temple has a verified location point and a reference photograph here.",
  latitude: 24.85,
  longitude: 79.93333333,
  coverImage: "/references/kandariya-mahadeva.jpg",
  coverAlt: "Kandariya Mahadeva Temple in the western group at Khajuraho",
  coverCredit: KANDARIYA_CREDIT,
  checkpoints: [
    {
      id: "khajuraho-kandariya",
      slug: "kandariya-mahadeva",
      name: "Kandariya Mahadeva Temple",
      category: "temple",
      shortDescription: "The largest historic temple at Khajuraho, dedicated to Shiva.",
      story:
        "The Kandariya Mahadeva Temple is the largest historic temple at Khajuraho and is dedicated to Shiva. It belongs to the 11th century. The tower rises above a sequence of halls, and the outer walls are covered with sculpture. The cover photograph of this destination is a view of this temple from the south, and it is the only reference image the scanner can use here.",
      latitude: 24.852972,
      longitude: 79.91956,
      radiusMeters: 35,
      referenceImageUrl: "/references/kandariya-mahadeva.jpg",
      referenceImageUrls: ["/references/kandariya-mahadeva.jpg"],
      imageCredit: KANDARIYA_CREDIT,
      sortOrder: 1,
    },
    {
      id: "khajuraho-lakshmana",
      slug: "lakshmana",
      name: "Lakshmana Temple",
      category: "temple",
      shortDescription: "A Vaishnava temple in the western group.",
      story:
        "The Lakshmana Temple stands in the western group and is dedicated to Vishnu. An inscription is read as recording its consecration in 954 CE. It has no reference photograph or separate location point in this guide, so it can be read but not scanned or fenced.",
      sortOrder: 2,
    },
    {
      id: "khajuraho-vishvanatha",
      slug: "vishvanatha",
      name: "Vishvanatha Temple",
      category: "temple",
      shortDescription: "A Shiva temple in the western group.",
      story:
        "The Vishvanatha Temple is a Shiva temple in the western group, generally placed in the early 11th century. No reference photograph or surveyed point for it is on record here.",
      sortOrder: 3,
    },
    {
      id: "khajuraho-parshvanatha",
      slug: "parshvanatha",
      name: "Parshvanatha Temple",
      category: "temple",
      shortDescription: "A Jain temple in the eastern group.",
      story:
        "The Parshvanatha Temple is a Jain temple in the eastern group at Khajuraho, dedicated to the tirthankara Parshvanatha. A construction year, a location point, and a reference photograph for it are not on record in this guide.",
      sortOrder: 4,
    },
  ],
};
