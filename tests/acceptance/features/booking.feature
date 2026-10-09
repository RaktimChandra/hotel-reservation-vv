Feature: Reserve a hotel room
  As a guest of Marina Crest
  I want to search, price and reserve rooms online
  So that my stay is guaranteed before I travel

  Background:
    Given the hotel has 20 rooms and today is 8 October 2026
    And a registered guest "Meera Iyer" is signed in

  @UAT-01
  Scenario: Guest books and pays for a deluxe room
    When the guest reserves 1 "DELUXE" room from "2026-11-02" to "2026-11-05" for 2 adults
    And pays with card "4111111111111111"
    Then the booking status is "CONFIRMED"
    And the amount charged is 12600.00 rupees

  @UAT-02
  Scenario: The last suite cannot be sold twice
    Given every "SUITE" is already booked from "2026-11-02" to "2026-11-05"
    When the guest tries to reserve 1 "SUITE" room from "2026-11-03" to "2026-11-04" for 1 adults
    Then the reservation is refused with "NO_AVAILABILITY"

  @UAT-03
  Scenario Outline: Refund depends on how early the guest cancels
    Given the guest holds a paid refundable "DELUXE" booking starting <days> days from today
    When the guest cancels the booking
    Then <percent> percent of the payment is refunded under rule "<rule>"

    Examples:
      | days | percent | rule |
      | 10   | 100     | R3   |
      | 4    | 50      | R4   |
      | 1    | 0       | R6   |

  @UAT-04
  Scenario: A non-refundable saver rate gives no refund
    Given the guest holds a paid non-refundable "STANDARD" booking starting 20 days from today
    When the guest cancels the booking
    Then 0 percent of the payment is refunded under rule "R2"
