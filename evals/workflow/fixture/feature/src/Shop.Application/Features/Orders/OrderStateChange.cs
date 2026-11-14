using Shop.Domain.Orders;

namespace Shop.Application.Features.Orders;

/// <summary>The outcome of a state write and the state the order had before it.</summary>
public sealed record OrderStateChange(OrderStateOutcome Outcome, OrderState Previous);
